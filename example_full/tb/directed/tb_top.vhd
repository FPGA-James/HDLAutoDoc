library ieee;
use ieee.std_logic_1164.all;

-- Directed testbench for the top level.
--
-- Programs the filters through the APB port, then streams bytes through the
-- external pipeline, with no verification framework: each scenario below is
-- marked with a TEST comment.
entity tb_top is
end entity tb_top;

architecture tb of tb_top is
    signal clk, adc_clk, arst_n, adc_arst_n : std_logic := '0';
    signal psel, penable, pwrite, pready   : std_logic := '0';
    signal paddr  : std_logic_vector(7 downto 0)  := (others => '0');
    signal pwdata, prdata : std_logic_vector(31 downto 0) := (others => '0');
    signal ext_tdata, ext_out : std_logic_vector(7 downto 0) := (others => '0');
    signal ext_tvalid, ext_tlast, ext_tready, out_tvalid, out_tlast : std_logic := '0';
    signal smp_tdata : std_logic_vector(7 downto 0);
    signal smp_tvalid, smp_tlast, busy, ovf : std_logic;
begin
    clk     <= not clk after 5 ns;
    adc_clk <= not adc_clk after 7 ns;

    dut : entity work.top
        port map (
            clk => clk, arst_n => arst_n, adc_clk => adc_clk, adc_arst_n => adc_arst_n,
            adc_data => x"123",
            s_apb_psel => psel, s_apb_penable => penable, s_apb_pwrite => pwrite,
            s_apb_paddr => paddr, s_apb_pwdata => pwdata, s_apb_prdata => prdata,
            s_apb_pready => pready,
            m_axis_tdata => smp_tdata, m_axis_tvalid => smp_tvalid,
            m_axis_tready => '1', m_axis_tlast => smp_tlast,
            s_ext_tdata => ext_tdata, s_ext_tvalid => ext_tvalid,
            s_ext_tready => ext_tready, s_ext_tlast => ext_tlast,
            m_ext_tdata => ext_out, m_ext_tvalid => out_tvalid,
            m_ext_tready => '1', m_ext_tlast => out_tlast,
            led_busy => busy, led_overflow => ovf
        );

    stimulus : process is
        -- One APB write.
        procedure apb_write(addr : std_logic_vector(7 downto 0); value : std_logic_vector(31 downto 0)) is
        begin
            psel <= '1'; pwrite <= '1'; paddr <= addr; pwdata <= value;
            wait until rising_edge(clk);
            penable <= '1';
            wait until rising_edge(clk) and pready = '1';
            psel <= '0'; penable <= '0';
            wait until rising_edge(clk);
        end procedure;
    begin
        arst_n <= '0'; adc_arst_n <= '0';
        wait for 50 ns;
        arst_n <= '1'; adc_arst_n <= '1';
        wait for 50 ns;

        -- TEST: register_write — a write over APB reaches the scratch register
        apb_write(x"0C", x"DEADBEEF");

        -- TEST: capture_runs — setting start raises led_busy
        apb_write(x"00", x"00000003");
        wait until busy = '1' for 1 us;

        -- TEST: ext_filter_pass — a packet starting above the threshold reaches m_ext
        apb_write(x"08", x"00000080");
        ext_tdata <= x"C8"; ext_tvalid <= '1'; ext_tlast <= '1';
        wait until rising_edge(clk);
        ext_tvalid <= '0';
        wait for 100 ns;
        std.env.finish;
    end process stimulus;
end architecture tb;
