library vunit_lib;
context vunit_lib.vunit_context;
library ieee;
use ieee.std_logic_1164.all;

-- Testbench for sample_ctrl.
--
-- Starts a capture and checks the controller arms, runs for its window, then
-- reports done and waits for the request to be withdrawn.
entity tb_sample_ctrl is
    generic (runner_cfg : string);
end entity tb_sample_ctrl;

architecture tb of tb_sample_ctrl is
    constant CYCLES : positive := 8;
    signal clk, rst, start, overflow, capture_en, busy : std_logic := '0';
    signal state_code : std_logic_vector(1 downto 0);
begin
    clk <= not clk after 5 ns;

    dut : entity work.sample_ctrl
        generic map (RUN_CYCLES => CYCLES)
        port map (clk => clk, rst => rst, start => start, overflow => overflow,
                  capture_en => capture_en, busy => busy, state_code => state_code);

    main : process is
    begin
        test_runner_setup(runner, runner_cfg);
        rst <= '1';
        wait for 20 ns;
        rst <= '0';

        -- The window opens after arming and lasts RUN_CYCLES cycles.
        if run("capture_window_length") then
            start <= '1';
            wait until capture_en = '1';
            wait until capture_en = '0';
            check_equal(state_code, std_logic_vector'("11"));

        -- Nothing runs without a start request.
        elsif run("idle_without_start") then
            wait for 100 ns;
            check_equal(busy, '0');

        -- An overflow ends the window early.
        elsif run("overflow_ends_window") then
            start <= '1';
            wait until capture_en = '1';
            overflow <= '1';
            wait until capture_en = '0';
            check_equal(state_code, std_logic_vector'("11"));
        end if;

        test_runner_cleanup(runner);
    end process main;
end architecture tb;
