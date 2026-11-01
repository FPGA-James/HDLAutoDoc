library ieee;
use ieee.std_logic_1164.all;

-- Sampler top level.
--
-- Captures samples from a converter clock into the system clock, runs a capture
-- window under register control (APB in, through an AXI4-Lite register file)
-- and sends the samples, and a second external byte stream, through packet
-- filters. The converter and system clocks are asynchronous to each other.
--
-- .. mermaid::
--    :caption: Top-level structure
--
--    flowchart LR
--      APB[s_apb] --> BR[apb_bridge] --> RG[axil_adapter + axil_regs]
--      RG -- start, threshold --> CT[sample_ctrl]
--      ADC[adc_data] --> CAP[sample_capture]
--      CT -- capture_en --> CAP
--      CAP --> SS[sample_stream] --> MA[m_axis]
--      EXT[s_ext] --> AP[axis_pipeline] --> ME[m_ext]
--      RG -- filter_enable --> SS
--      RG -- filter_enable --> AP
entity top is
    generic (
        -- Length of the capture window in system clock cycles.
        WINDOW_CYCLES : positive := 1024
    );
    port (
        -- System clock.
        clk            : in  std_logic;
        -- System-domain asynchronous active-low reset input.
        arst_n         : in  std_logic;
        -- Converter clock; asynchronous to clk.
        adc_clk        : in  std_logic;
        -- Converter-domain asynchronous active-low reset input.
        adc_arst_n     : in  std_logic;
        -- Sample from the converter.
        adc_data       : in  std_logic_vector(11 downto 0);
        -- APB subordinate port for register access.
        s_apb_psel     : in  std_logic;
        s_apb_penable  : in  std_logic;
        s_apb_pwrite   : in  std_logic;
        s_apb_paddr    : in  std_logic_vector(7 downto 0);
        s_apb_pwdata   : in  std_logic_vector(31 downto 0);
        s_apb_prdata   : out std_logic_vector(31 downto 0);
        s_apb_pready   : out std_logic;
        -- Filtered captured samples (low byte, one-byte packets).
        m_axis_tdata   : out std_logic_vector(7 downto 0);
        m_axis_tvalid  : out std_logic;
        m_axis_tready  : in  std_logic;
        m_axis_tlast   : out std_logic;
        -- External byte stream in.
        s_ext_tdata    : in  std_logic_vector(7 downto 0);
        s_ext_tvalid   : in  std_logic;
        s_ext_tready   : out std_logic;
        s_ext_tlast    : in  std_logic;
        -- External byte stream out, after filtering.
        m_ext_tdata    : out std_logic_vector(7 downto 0);
        m_ext_tvalid   : out std_logic;
        m_ext_tready   : in  std_logic;
        m_ext_tlast    : out std_logic;
        -- High while a capture is in progress.
        led_busy       : out std_logic;
        -- High after a sample was lost to a full FIFO.
        led_overflow   : out std_logic
    );
end entity top;

architecture rtl of top is

    -- The components below are SystemVerilog modules; the synthesis flow
    -- resolves them by name. Their widths follow full_pkg::SAMPLE_W (12).
    component sample_capture is
        port (
            clk          : in  std_logic;
            rst_n        : in  std_logic;
            enable       : in  std_logic;
            adc_clk      : in  std_logic;
            adc_rst      : in  std_logic;
            adc_data     : in  std_logic_vector(11 downto 0);
            sample_data  : out std_logic_vector(11 downto 0);
            sample_valid : out std_logic;
            sample_ready : in  std_logic;
            overflow     : out std_logic
        );
    end component sample_capture;

    component sample_stream is
        port (
            clk           : in  std_logic;
            rst           : in  std_logic;
            enable        : in  std_logic;
            threshold     : in  std_logic_vector(7 downto 0);
            sample_data   : in  std_logic_vector(11 downto 0);
            sample_valid  : in  std_logic;
            sample_ready  : out std_logic;
            m_axis_tdata  : out std_logic_vector(7 downto 0);
            m_axis_tvalid : out std_logic;
            m_axis_tready : in  std_logic;
            m_axis_tlast  : out std_logic
        );
    end component sample_stream;

    component axis_pipeline is
        port (
            clk           : in  std_logic;
            rst           : in  std_logic;
            enable        : in  std_logic;
            clear         : in  std_logic;
            threshold     : in  std_logic_vector(7 downto 0);
            s_axis_tdata  : in  std_logic_vector(7 downto 0);
            s_axis_tvalid : in  std_logic;
            s_axis_tready : out std_logic;
            s_axis_tlast  : in  std_logic;
            m_axis_tdata  : out std_logic_vector(7 downto 0);
            m_axis_tvalid : out std_logic;
            m_axis_tready : in  std_logic;
            m_axis_tlast  : out std_logic;
            count         : out std_logic_vector(15 downto 0)
        );
    end component axis_pipeline;

    component axil_adapter is
        port (
            clk            : in  std_logic;
            rst            : in  std_logic;
            s_axil_awaddr  : in  std_logic_vector(7 downto 0);
            s_axil_awvalid : in  std_logic;
            s_axil_awready : out std_logic;
            s_axil_wdata   : in  std_logic_vector(31 downto 0);
            s_axil_wstrb   : in  std_logic_vector(3 downto 0);
            s_axil_wvalid  : in  std_logic;
            s_axil_wready  : out std_logic;
            s_axil_bresp   : out std_logic_vector(1 downto 0);
            s_axil_bvalid  : out std_logic;
            s_axil_bready  : in  std_logic;
            s_axil_araddr  : in  std_logic_vector(7 downto 0);
            s_axil_arvalid : in  std_logic;
            s_axil_arready : out std_logic;
            s_axil_rdata   : out std_logic_vector(31 downto 0);
            s_axil_rresp   : out std_logic_vector(1 downto 0);
            s_axil_rvalid  : out std_logic;
            s_axil_rready  : in  std_logic;
            start          : out std_logic;
            filter_enable  : out std_logic;
            clear          : out std_logic;
            threshold      : out std_logic_vector(7 downto 0);
            state_code     : in  std_logic_vector(1 downto 0);
            overflow       : in  std_logic;
            count          : in  std_logic_vector(15 downto 0)
        );
    end component axil_adapter;

    -- Resets: asserted at once, released on the domain's clock.
    signal srst_n, adc_srst_n : std_logic;
    signal rst, adc_rst       : std_logic;

    -- Register bus between the APB bridge and the register file.
    signal awaddr, araddr   : std_logic_vector(7 downto 0);
    signal wdata, rdata     : std_logic_vector(31 downto 0);
    signal wstrb            : std_logic_vector(3 downto 0);
    signal bresp, rresp     : std_logic_vector(1 downto 0);
    signal awvalid, awready, wvalid, wready, bvalid, bready : std_logic;
    signal arvalid, arready, rvalid, rready                 : std_logic;

    -- Control.
    signal start, filter_enable, clear : std_logic;
    signal threshold                   : std_logic_vector(7 downto 0);
    signal capture_en, busy            : std_logic;
    signal state_code                  : std_logic_vector(1 downto 0);
    signal ext_count                   : std_logic_vector(15 downto 0);

    -- Capture path.
    signal sample_data  : std_logic_vector(11 downto 0);
    signal sample_valid, sample_ready : std_logic;
    signal overflow     : std_logic;
    -- overflow is set on adc_clk; two flops bring it onto clk.
    signal ovf_meta, ovf_sync : std_logic := '0';

begin

    -- System-domain reset.
    u_rst_sys : entity work.reset_sync
        port map (clk => clk, arst_n => arst_n, srst_n => srst_n);

    -- Converter-domain reset.
    u_rst_adc : entity work.reset_sync
        port map (clk => adc_clk, arst_n => adc_arst_n, srst_n => adc_srst_n);

    rst     <= not srst_n;
    adc_rst <= not adc_srst_n;

    -- p_ovf_sync: Brings the converter-domain overflow flag onto clk.
    p_ovf_sync : process(clk) is
    begin
        if rising_edge(clk) then
            ovf_meta <= overflow;
            ovf_sync <= ovf_meta;
        end if;
    end process p_ovf_sync;

    led_busy     <= busy;
    led_overflow <= ovf_sync;

    -- Register access: APB to AXI4-Lite to the register file.
    u_apb : entity work.apb_bridge
        port map (
            clk => clk, rst => rst,
            s_apb_psel => s_apb_psel, s_apb_penable => s_apb_penable,
            s_apb_pwrite => s_apb_pwrite, s_apb_paddr => s_apb_paddr,
            s_apb_pwdata => s_apb_pwdata, s_apb_prdata => s_apb_prdata,
            s_apb_pready => s_apb_pready,
            m_axil_awaddr => awaddr, m_axil_awvalid => awvalid, m_axil_awready => awready,
            m_axil_wdata => wdata, m_axil_wstrb => wstrb,
            m_axil_wvalid => wvalid, m_axil_wready => wready,
            m_axil_bresp => bresp, m_axil_bvalid => bvalid, m_axil_bready => bready,
            m_axil_araddr => araddr, m_axil_arvalid => arvalid, m_axil_arready => arready,
            m_axil_rdata => rdata, m_axil_rresp => rresp,
            m_axil_rvalid => rvalid, m_axil_rready => rready
        );

    u_regs : axil_adapter
        port map (
            clk => clk, rst => rst,
            s_axil_awaddr => awaddr, s_axil_awvalid => awvalid, s_axil_awready => awready,
            s_axil_wdata => wdata, s_axil_wstrb => wstrb,
            s_axil_wvalid => wvalid, s_axil_wready => wready,
            s_axil_bresp => bresp, s_axil_bvalid => bvalid, s_axil_bready => bready,
            s_axil_araddr => araddr, s_axil_arvalid => arvalid, s_axil_arready => arready,
            s_axil_rdata => rdata, s_axil_rresp => rresp,
            s_axil_rvalid => rvalid, s_axil_rready => rready,
            start => start, filter_enable => filter_enable, clear => clear,
            threshold => threshold, state_code => state_code,
            overflow => ovf_sync, count => ext_count
        );

    -- Capture window control.
    u_ctrl : entity work.sample_ctrl
        generic map (RUN_CYCLES => WINDOW_CYCLES)
        port map (
            clk => clk, rst => rst, start => start, overflow => ovf_sync,
            capture_en => capture_en, busy => busy, state_code => state_code
        );

    -- Capture across the clock boundary.
    u_capture : sample_capture
        port map (
            clk => clk, rst_n => srst_n, enable => capture_en,
            adc_clk => adc_clk, adc_rst => adc_rst, adc_data => adc_data,
            sample_data => sample_data, sample_valid => sample_valid,
            sample_ready => sample_ready, overflow => overflow
        );

    -- Captured samples through the packet filter.
    u_samples : sample_stream
        port map (
            clk => clk, rst => rst, enable => filter_enable, threshold => threshold,
            sample_data => sample_data, sample_valid => sample_valid,
            sample_ready => sample_ready,
            m_axis_tdata => m_axis_tdata, m_axis_tvalid => m_axis_tvalid,
            m_axis_tready => m_axis_tready, m_axis_tlast => m_axis_tlast
        );

    -- External stream through the packet filter.
    u_ext : axis_pipeline
        port map (
            clk => clk, rst => rst, enable => filter_enable, clear => clear,
            threshold => threshold,
            s_axis_tdata => s_ext_tdata, s_axis_tvalid => s_ext_tvalid,
            s_axis_tready => s_ext_tready, s_axis_tlast => s_ext_tlast,
            m_axis_tdata => m_ext_tdata, m_axis_tvalid => m_ext_tvalid,
            m_axis_tready => m_ext_tready, m_axis_tlast => m_ext_tlast,
            count => ext_count
        );

end architecture rtl;
