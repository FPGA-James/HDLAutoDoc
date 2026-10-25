library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Blinky LED controller.
--
-- Implements a 3-state FSM that drives an LED through a repeating
-- ON -> FADE -> OFF sequence. Each state is held for a configurable
-- number of clock cycles determined by an external timer pulse.
--
-- State sequence: ON -> FADE -> OFF -> ON -> ...
entity blinky is
    port (
        -- System clock, rising-edge triggered.
        clk       : in  std_logic;
        -- Synchronous active-high reset. Returns FSM to OFF state.
        rst       : in  std_logic;
        -- Enable signal. FSM only advances when en is asserted.
        en        : in  std_logic;
        -- Phase timer expiry pulse. Must be high for exactly one cycle.
        timer_exp : in  std_logic;
        -- LED full-brightness drive.
        led_on    : out std_logic;
        -- LED half-brightness PWM drive (fade effect).
        led_fade  : out std_logic;
        -- LED off indicator (all drives deasserted).
        led_off   : out std_logic
    );
end entity blinky;

-- RTL implementation using a 3-process Moore FSM style.
architecture rtl of blinky is

    -- FSM state type encoding the three LED phases.
    type t_state is (
        -- LED fully illuminated.
        ON_STATE,
        -- LED dimming via PWM (fade transition).
        FADE_STATE,
        -- LED completely off.
        OFF_STATE
    );

    -- Current state register, initialised to OFF at power-on.
    signal state      : t_state := OFF_STATE;
    -- Next state combinational signal.
    signal next_state : t_state;

begin

    -- p_state_reg: Clocked state register.
    --
    -- Captures next_state on each rising edge of clk.
    -- Synchronous reset drives state back to OFF_STATE.
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "clk",       "wave": "P......." },
    --      { "name": "rst",       "wave": "1.0....." },
    --      { "name": "en",        "wave": "0......." },
    --      { "name": "state",     "wave": "=.=.....", "data": ["(any)","OFF"] },
    --      { "name": "led_on",    "wave": "x.0....." },
    --      { "name": "led_fade",  "wave": "x.0....." },
    --      { "name": "led_off",   "wave": "x.1....." }
    --    ]}
    p_state_reg : process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                state <= OFF_STATE;
            else
                state <= next_state;
            end if;
        end if;
    end process p_state_reg;

    -- p_next_state: Combinational next-state logic.
    --
    -- FSM only advances when both en and timer_exp are asserted.
    -- If en is deasserted the state holds regardless of timer_exp.
    --
    -- Transitions:
    --   OFF_STATE  + en + timer_exp -> ON_STATE
    --   ON_STATE   + en + timer_exp -> FADE_STATE
    --   FADE_STATE + en + timer_exp -> OFF_STATE
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "clk",       "wave": "P............." },
    --      { "name": "en",        "wave": "01...........0" },
    --      { "name": "timer_exp", "wave": "0..1..1..1..0." },
    --      { "name": "state",     "wave": "=..=..=..=..=.",
    --        "data": ["OFF","ON","FADE","OFF","OFF"] },
    --      { "name": "led_on",    "wave": "0..1..0..0..0." },
    --      { "name": "led_fade",  "wave": "0..0..1..0..0." },
    --      { "name": "led_off",   "wave": "1..0..0..1..1." }
    --    ]}
    p_next_state : process(state, en, timer_exp)
    begin
        next_state <= state;

        if en = '1' and timer_exp = '1' then
            case state is
                when OFF_STATE  => next_state <= ON_STATE;
                when ON_STATE   => next_state <= FADE_STATE;
                when FADE_STATE => next_state <= OFF_STATE;
            end case;
        end if;
    end process p_next_state;

    -- p_outputs: Combinational Moore output decode.
    --
    -- Drives LED outputs based solely on current state.
    -- All outputs default to 0 before the case statement to
    -- prevent latches during synthesis.
    --
    -- Output truth table:
    --   OFF_STATE  -> led_on=0 led_fade=0 led_off=1
    --   ON_STATE   -> led_on=1 led_fade=0 led_off=0
    --   FADE_STATE -> led_on=0 led_fade=1 led_off=0
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "state",    "wave": "=.=.=.=.",
    --        "data": ["OFF","ON","FADE","OFF"] },
    --      { "name": "led_on",   "wave": "0.1.0.0." },
    --      { "name": "led_fade", "wave": "0.0.1.0." },
    --      { "name": "led_off",  "wave": "1.0.0.1." }
    --    ]}
    p_outputs : process(state)
    begin
        led_on   <= '0';
        led_fade <= '0';
        led_off  <= '0';

        case state is
            when OFF_STATE  => led_off  <= '1';
            when ON_STATE   => led_on   <= '1';
            when FADE_STATE => led_fade <= '1';
        end case;
    end process p_outputs;

end architecture rtl;