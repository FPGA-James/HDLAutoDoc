-- Top-level integration module.
--
-- Instantiates the traffic_light controller, blinky LED module, PWM
-- controller, and cfg_sync. Runtime configuration (blinky enable and PWM
-- duty cycle) arrives on a slow config bus clock and is synchronised into
-- the main 50 MHz domain by cfg_sync.
library ieee;
use ieee.std_logic_1164.all;

entity top is
    port (
        -- System clock 50 MHz.
        clk          : in  std_logic;
        -- Synchronous active-high reset (sys_clk domain).
        rst          : in  std_logic;
        -- Config bus clock (slow, e.g. 10 MHz from external MCU).
        cfg_clk      : in  std_logic;
        -- Synchronous active-high reset (cfg_clk domain).
        cfg_rst      : in  std_logic;
        -- Config inputs (cfg_clk domain).
        mode_sel     : in  std_logic;
        duty_cycle   : in  std_logic_vector(7 downto 0);
        -- Traffic light outputs.
        red_out      : out std_logic;
        amber_out    : out std_logic;
        green_out    : out std_logic;
        -- Blinky LED outputs.
        led_on       : out std_logic;
        led_fade     : out std_logic;
        led_off      : out std_logic;
        -- PWM output for LED fading (shared).
        pwm_out      : out std_logic
    );
end entity top;

architecture rtl of top is

    signal timer_exp   : std_logic;
    signal blinky_en   : std_logic;
    signal pwm_duty    : std_logic_vector(7 downto 0);
    signal period_done : std_logic;

begin

    -- u_cfg_sync: Synchronise config bus inputs into the system clock domain.
    u_cfg_sync : entity work.cfg_sync
        port map (
            sys_clk    => clk,
            sys_rst    => rst,
            cfg_clk    => cfg_clk,
            cfg_rst    => cfg_rst,
            mode_sel   => mode_sel,
            duty_cycle => duty_cycle,
            blinky_en  => blinky_en,
            pwm_duty   => pwm_duty
        );

    -- u_traffic_light: Traffic light FSM instance.
    u_traffic_light : entity work.traffic_light
        port map (
            clk       => clk,
            rst       => rst,
            timer_exp => timer_exp,
            red_out   => red_out,
            amber_out => amber_out,
            green_out => green_out
        );

    -- u_blinky: Blinky LED FSM instance.
    u_blinky : entity work.blinky
        port map (
            clk       => clk,
            rst       => rst,
            en        => blinky_en,
            timer_exp => timer_exp,
            led_on    => led_on,
            led_fade  => led_fade,
            led_off   => led_off
        );

    -- u_pwm: PWM controller shared between traffic light and blinky fade.
    u_pwm : entity work.pwm_controller
        port map (
            clk         => clk,
            rst         => rst,
            en          => blinky_en,
            duty_i      => pwm_duty,
            pwm_o       => pwm_out,
            period_done => period_done
        );

end architecture rtl;
