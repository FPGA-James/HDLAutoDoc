library ieee;
use ieee.std_logic_1164.all;

-- Sampler controller.
--
-- Runs one capture window per start request: it arms, enables the capture
-- path for RUN_CYCLES clock cycles (or until the FIFO overflows), then reports
-- done and waits for the request to be withdrawn before it can run again.
--
-- State sequence: IDLE -> ARMED -> RUN -> DONE -> IDLE.
entity sample_ctrl is
    generic (
        -- Length of the capture window in clock cycles.
        RUN_CYCLES : positive := 1024
    );
    port (
        -- System clock, rising-edge triggered.
        clk        : in  std_logic;
        -- Synchronous active-high reset. Returns the FSM to IDLE.
        rst        : in  std_logic;
        -- Start request; held high until the capture is done.
        start      : in  std_logic;
        -- A sample was lost; ends the window early.
        overflow   : in  std_logic;
        -- High while samples should be captured.
        capture_en : out std_logic;
        -- High from arming until the request is withdrawn.
        busy       : out std_logic;
        -- Current state, 0 IDLE, 1 ARMED, 2 RUN, 3 DONE.
        state_code : out std_logic_vector(1 downto 0)
    );
end entity sample_ctrl;

architecture rtl of sample_ctrl is

    -- FSM state type for the capture window.
    type t_state is (
        -- Waiting for a start request.
        IDLE,
        -- Request seen; capture path is being enabled.
        ARMED,
        -- Capturing samples.
        RUN,
        -- Window over; waiting for the request to drop.
        DONE
    );

    signal state      : t_state := IDLE;
    signal next_state : t_state;
    -- Cycles spent in RUN.
    signal run_cnt    : natural range 0 to RUN_CYCLES - 1 := 0;
    -- High on the last cycle of the window.
    signal run_last   : std_logic;

begin

    run_last <= '1' when run_cnt = RUN_CYCLES - 1 else '0';

    -- p_state_reg: Clocked state register and window counter.
    --
    -- Synchronous reset returns the state to IDLE and clears the counter.
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "clk",   "wave": "P......." },
    --      { "name": "rst",   "wave": "1.0....." },
    --      { "name": "start", "wave": "0..1...." },
    --      { "name": "state", "wave": "=.=.=.=.", "data": ["(any)","IDLE","ARMED","RUN"] }
    --    ]}
    p_state_reg : process(clk) is
    begin
        if rising_edge(clk) then
            if rst = '1' then
                state   <= IDLE;
                run_cnt <= 0;
            else
                state <= next_state;
                if state = RUN then
                    if run_cnt = RUN_CYCLES - 1 then
                        run_cnt <= 0;
                    else
                        run_cnt <= run_cnt + 1;
                    end if;
                else
                    run_cnt <= 0;
                end if;
            end if;
        end if;
    end process p_state_reg;

    -- p_next_state: Combinational next-state logic.
    --
    -- A start request arms the controller; the window ends after RUN_CYCLES
    -- cycles or on overflow; DONE is left when the request is withdrawn.
    --
    -- .. mermaid::
    --    :caption: Controller states
    --
    --    stateDiagram-v2
    --      [*] --> IDLE
    --      IDLE --> ARMED: start
    --      ARMED --> RUN
    --      RUN --> DONE: window over or overflow
    --      DONE --> IDLE: start withdrawn
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "clk",      "wave": "P........" },
    --      { "name": "start",    "wave": "01......0" },
    --      { "name": "run_last", "wave": "0....10.." },
    --      { "name": "state",    "wave": "=.=.=.=.=", "data": ["IDLE","ARMED","RUN","DONE","IDLE"] }
    --    ]}
    p_next_state : process(state, start, overflow, run_last) is
    begin
        next_state <= state;

        case state is
            when IDLE =>
                if start = '1' then
                    next_state <= ARMED;
                end if;

            when ARMED =>
                next_state <= RUN;

            when RUN =>
                if run_last = '1' then
                    next_state <= DONE;
                elsif overflow = '1' then
                    next_state <= DONE;
                end if;

            when DONE =>
                if start = '0' then
                    next_state <= IDLE;
                end if;
        end case;
    end process p_next_state;

    -- p_outputs: Combinational Moore output decode.
    --
    -- Capture is enabled in RUN only; busy covers everything but IDLE.
    p_outputs : process(state) is
    begin
        capture_en <= '0';
        busy       <= '1';
        state_code <= "00";

        case state is
            when IDLE  => busy <= '0';
            when ARMED => state_code <= "01";
            when RUN   => capture_en <= '1'; state_code <= "10";
            when DONE  => state_code <= "11";
        end case;
    end process p_outputs;

end architecture rtl;
