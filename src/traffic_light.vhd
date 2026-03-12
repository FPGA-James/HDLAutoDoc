library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Traffic light controller.
--
-- Implements a standard UK traffic light sequencer with four states:
-- RED, RED_AMBER, GREEN, and AMBER. The FSM advances on each rising
-- clock edge when timer_exp is asserted.
--
-- State sequence: RED -> RED_AMBER -> GREEN -> AMBER -> RED.
entity traffic_light is
    generic (
        -- System clock frequency in Hz. Used to derive phase timer counts.
        CLK_FREQ_HZ  : natural := 50_000_000;
        -- Duration of the RED and GREEN phases in milliseconds.
        PHASE_MS     : natural := 5_000;
        -- Duration of the RED_AMBER and AMBER transition phases in milliseconds.
        TRANS_MS     : natural := 2_000
    );
    port (
        -- System clock, rising-edge triggered.
        clk       : in  std_logic;
        -- Synchronous active-high reset. Returns FSM to RED state.
        rst       : in  std_logic;
        -- Phase timer expiry pulse. Must be high for exactly one cycle.
        timer_exp : in  std_logic;
        -- Red lamp drive. Asserted in RED and RED_AMBER states.
        red_out   : out std_logic;
        -- Amber lamp drive. Asserted in RED_AMBER and AMBER states.
        amber_out : out std_logic;
        -- Green lamp drive. Asserted in GREEN state only.
        green_out : out std_logic
    );
end entity traffic_light;

-- RTL implementation using a 3-process Moore FSM style.
architecture rtl of traffic_light is

    -- FSM state type encoding all four traffic light phases.
    type t_state is (
        -- Red light only. Vehicles must remain stopped.
        RED,
        -- Red and amber simultaneously. Vehicles prepare to move.
        RED_AMBER,
        -- Green light. Vehicles may proceed.
        GREEN,
        -- Amber light only. Vehicles prepare to stop.
        AMBER
    );

    -- Current state register, initialised to RED at power-on.
    signal state      : t_state := RED;
    -- Next state combinational signal, feeds state register.
    signal next_state : t_state;

begin

    -- p_state_reg: Clocked state register.
    --
    -- Captures next_state on each rising edge of clk.
    -- When rst is asserted the state returns to RED synchronously,
    -- regardless of timer_exp or next_state.
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "clk",   "wave": "P......." },
    --      { "name": "rst",   "wave": "1.0....." },
    --      { "name": "state", "wave": "=.=.....", "data": ["(any)","RED"] },
    --      { "name": "red",   "wave": "x.1....." }
    --    ]}
    p_state_reg : process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                state <= RED;
            else
                state <= next_state;
            end if;
        end if;
    end process p_state_reg;

    -- p_next_state: Combinational next-state logic.
    --
    -- Evaluates the FSM transition function. Default assignment
    -- next_state <= state implements hold when timer_exp is low.
    -- All four transitions are guarded solely by timer_exp = 1.
    --
    -- Transitions:
    --   RED       + timer_exp -> RED_AMBER
    --   RED_AMBER + timer_exp -> GREEN
    --   GREEN     + timer_exp -> AMBER
    --   AMBER     + timer_exp -> RED
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "clk",       "wave": "P........." },
    --      { "name": "timer_exp", "wave": "0.1.1.1.1." },
    --      { "name": "state",     "wave": "=.=.=.=.=.",
    --        "data": ["RED","RED_AMB","GREEN","AMBER","RED"] },
    --      { "name": "red_out",   "wave": "1.1.0.0.1." },
    --      { "name": "amber_out", "wave": "0.1.0.1.0." },
    --      { "name": "green_out", "wave": "0.0.1.0.0." }
    --    ]}
    p_next_state : process(state, timer_exp)
    begin
        next_state <= state;

        case state is
            when RED =>
                if timer_exp = '1' then
                    next_state <= RED_AMBER;
                end if;

            when RED_AMBER =>
                if timer_exp = '1' then
                    next_state <= GREEN;
                end if;

            when GREEN =>
                if timer_exp = '1' then
                    next_state <= AMBER;
                end if;

            when AMBER =>
                if timer_exp = '1' then
                    next_state <= RED;
                end if;
        end case;
    end process p_next_state;

    -- p_outputs: Combinational Moore output decode.
    --
    -- Drives lamp outputs based solely on current state.
    -- All outputs default to 0 before the case statement to
    -- prevent latches during synthesis.
    --
    -- Output truth table:
    --   RED       -> red=1 amber=0 green=0
    --   RED_AMBER -> red=1 amber=1 green=0
    --   GREEN     -> red=0 amber=0 green=1
    --   AMBER     -> red=0 amber=1 green=0
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "state",     "wave": "=.=.=.=.",
    --        "data": ["RED","RED_AMB","GREEN","AMBER"] },
    --      { "name": "red_out",   "wave": "1.1.0.0." },
    --      { "name": "amber_out", "wave": "0.1.0.1." },
    --      { "name": "green_out", "wave": "0.0.1.0." }
    --    ]}
    p_outputs : process(state)
    begin
        red_out   <= '0';
        amber_out <= '0';
        green_out <= '0';

        case state is
            -- define red
            when RED       => red_out <= '1';
            when RED_AMBER => red_out <= '1'; amber_out <= '1';
            when GREEN     => green_out <= '1';
            when AMBER     => amber_out <= '1';
        end case;
    end process p_outputs;

end architecture rtl;