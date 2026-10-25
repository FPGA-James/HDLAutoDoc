-- Configuration synchroniser.
--
-- Receives runtime configuration from a slow config bus clock domain
-- (cfg_clk, e.g. 10 MHz from an external microcontroller) and makes it
-- available in the main system clock domain (sys_clk, 50 MHz).
--
-- mode_sel   crosses via a two-flop synchroniser (safe).
-- duty_cycle crosses as a raw multi-bit bus with no synchronisation
--            (unsafe — included to demonstrate CDC detection; a real
--            design should use a handshake or grey-code scheme here).
library ieee;
use ieee.std_logic_1164.all;

entity cfg_sync is
    port (
        -- System clock domain (50 MHz).
        sys_clk    : in  std_logic;
        -- Synchronous active-high reset (sys_clk domain).
        sys_rst    : in  std_logic;
        -- Config clock domain (slow bus clock).
        cfg_clk    : in  std_logic;
        -- Synchronous active-high reset (cfg_clk domain).
        cfg_rst    : in  std_logic;
        -- Config inputs (cfg_clk domain).
        -- Blinky enable: 1 = blinky LED active.
        mode_sel   : in  std_logic;
        -- PWM duty cycle: 0x00 = 0 %, 0xFF = 100 %.
        duty_cycle : in  std_logic_vector(7 downto 0);
        -- Outputs (sys_clk domain).
        -- Synchronised blinky enable (two-flop).
        blinky_en  : out std_logic;
        -- PWM duty cycle (unsynchronised crossing).
        pwm_duty   : out std_logic_vector(7 downto 0)
    );
end entity cfg_sync;

architecture rtl of cfg_sync is

    -- cfg_clk domain registers
    signal mode_sel_r   : std_logic;
    signal duty_cycle_r : std_logic_vector(7 downto 0);

    -- sys_clk domain: two-flop synchroniser pipeline for mode_sel_r
    signal mode_meta    : std_logic;
    signal mode_sync_r  : std_logic;

begin

    -- p_cfg_reg: Register config inputs in the cfg_clk domain.
    --
    -- Provides a stable registered version of mode_sel and duty_cycle
    -- before they cross into the sys_clk domain.
    p_cfg_reg : process(cfg_clk) is
    begin
        if rising_edge(cfg_clk) then
            if cfg_rst = '1' then
                mode_sel_r   <= '0';
                duty_cycle_r <= (others => '0');
            else
                mode_sel_r   <= mode_sel;
                duty_cycle_r <= duty_cycle;
            end if;
        end if;
    end process p_cfg_reg;

    -- p_mode_sync: Two-flop synchroniser for mode_sel_r (cfg_clk → sys_clk).
    --
    -- mode_sel_r is sampled twice in the sys_clk domain to resolve
    -- metastability before the signal is used by downstream logic.
    --
    -- .. wavedrom::
    --
    --    { "signal": [
    --      { "name": "cfg_clk",    "wave": "p........" },
    --      { "name": "sys_clk",    "wave": "P........" },
    --      { "name": "mode_sel_r", "wave": "0...1...." },
    --      { "name": "mode_meta",  "wave": "0....1..." },
    --      { "name": "mode_sync_r","wave": "0.....1.." }
    --    ]}
    p_mode_sync : process(sys_clk) is
    begin
        if rising_edge(sys_clk) then
            if sys_rst = '1' then
                mode_meta   <= '0';
                mode_sync_r <= '0';
            else
                mode_meta   <= mode_sel_r;
                mode_sync_r <= mode_meta;
            end if;
        end if;
    end process p_mode_sync;

    -- p_duty_capture: Capture duty_cycle_r directly in the sys_clk domain.
    --
    -- WARNING: This is an unsynchronised multi-bit crossing. duty_cycle_r is
    -- driven in the cfg_clk domain and sampled here without a handshake or
    -- grey-code scheme. Glitches are possible if both bits change together
    -- near a sys_clk edge. A proper implementation should use a handshake
    -- protocol or an async FIFO.
    p_duty_capture : process(sys_clk) is
    begin
        if rising_edge(sys_clk) then
            if sys_rst = '1' then
                pwm_duty <= (others => '0');
            else
                pwm_duty <= duty_cycle_r;
            end if;
        end if;
    end process p_duty_capture;

    blinky_en <= mode_sync_r;

end architecture rtl;
