-- Top-level integration module.
--
-- Instantiates the traffic_light controller and the blinky LED module.
-- The PWM controller is shared between both to drive the LED fade output.
library ieee;
use ieee.std_logic_1164.all;

entity top is
    port (
        -- System clock 50 MHz.
        clk         : in  std_logic;
        -- Synchronous active-high reset.
        rst         : in  std_logic;
        -- Traffic light outputs.
        red_out     : out std_logic;
        amber_out   : out std_logic;
        green_out   : out std_logic;
        -- Blinky LED outputs.
        led_on      : out std_logic;
        led_fade    : out std_logic;
        led_off     : out std_logic;
        -- PWM output for LED fading (shared).
        pwm_out     : out std_logic
    );
end entity top;

architecture rtl of top is

    signal timer_exp    : std_logic;
    signal blinky_en    : std_logic;
    signal pwm_duty     : std_logic_vector(7 downto 0);
    signal period_done  : std_logic;

begin

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