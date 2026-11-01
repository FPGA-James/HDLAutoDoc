library ieee;
use ieee.std_logic_1164.all;

-- APB to AXI4-Lite bridge.
--
-- Turns each APB transfer into one AXI4-Lite read or write and completes the
-- APB access when the AXI4-Lite response arrives. One transfer at a time.
entity apb_bridge is
    port (
        -- System clock.
        clk           : in  std_logic;
        -- Synchronous active-high reset.
        rst           : in  std_logic;
        -- APB subordinate port.
        s_apb_psel    : in  std_logic;
        s_apb_penable : in  std_logic;
        s_apb_pwrite  : in  std_logic;
        s_apb_paddr   : in  std_logic_vector(7 downto 0);
        s_apb_pwdata  : in  std_logic_vector(31 downto 0);
        s_apb_prdata  : out std_logic_vector(31 downto 0);
        s_apb_pready  : out std_logic;
        -- AXI4-Lite manager port.
        m_axil_awaddr  : out std_logic_vector(7 downto 0);
        m_axil_awvalid : out std_logic;
        m_axil_awready : in  std_logic;
        m_axil_wdata   : out std_logic_vector(31 downto 0);
        m_axil_wstrb   : out std_logic_vector(3 downto 0);
        m_axil_wvalid  : out std_logic;
        m_axil_wready  : in  std_logic;
        m_axil_bresp   : in  std_logic_vector(1 downto 0);
        m_axil_bvalid  : in  std_logic;
        m_axil_bready  : out std_logic;
        m_axil_araddr  : out std_logic_vector(7 downto 0);
        m_axil_arvalid : out std_logic;
        m_axil_arready : in  std_logic;
        m_axil_rdata   : in  std_logic_vector(31 downto 0);
        m_axil_rresp   : in  std_logic_vector(1 downto 0);
        m_axil_rvalid  : in  std_logic;
        m_axil_rready  : out std_logic
    );
end entity apb_bridge;

architecture rtl of apb_bridge is
    type t_phase is (IDLE, WR_ADDR, WR_RESP, RD_ADDR, RD_DATA, FINISH);
    signal phase : t_phase := IDLE;
    signal addr  : std_logic_vector(7 downto 0)  := (others => '0');
    signal wdata : std_logic_vector(31 downto 0) := (others => '0');
    signal rdata : std_logic_vector(31 downto 0) := (others => '0');
begin

    -- p_phase: Walks one APB transfer through the AXI4-Lite channels.
    p_phase : process(clk) is
    begin
        if rising_edge(clk) then
            if rst = '1' then
                phase <= IDLE;
            else
                case phase is
                    when IDLE =>
                        if s_apb_psel = '1' and s_apb_penable = '0' then
                            addr  <= s_apb_paddr;
                            wdata <= s_apb_pwdata;
                            if s_apb_pwrite = '1' then
                                phase <= WR_ADDR;
                            else
                                phase <= RD_ADDR;
                            end if;
                        end if;
                    when WR_ADDR =>
                        if m_axil_awready = '1' then
                            phase <= WR_RESP;
                        end if;
                    when WR_RESP =>
                        if m_axil_bvalid = '1' then
                            phase <= FINISH;
                        end if;
                    when RD_ADDR =>
                        if m_axil_arready = '1' then
                            phase <= RD_DATA;
                        end if;
                    when RD_DATA =>
                        if m_axil_rvalid = '1' then
                            rdata <= m_axil_rdata;
                            phase <= FINISH;
                        end if;
                    when FINISH =>
                        if s_apb_penable = '1' then
                            phase <= IDLE;
                        end if;
                end case;
            end if;
        end if;
    end process p_phase;

    m_axil_awaddr  <= addr;
    m_axil_awvalid <= '1' when phase = WR_ADDR else '0';
    m_axil_wdata   <= wdata;
    m_axil_wstrb   <= "1111";
    m_axil_wvalid  <= '1' when phase = WR_ADDR else '0';
    m_axil_bready  <= '1' when phase = WR_RESP else '0';
    m_axil_araddr  <= addr;
    m_axil_arvalid <= '1' when phase = RD_ADDR else '0';
    m_axil_rready  <= '1' when phase = RD_DATA else '0';

    s_apb_prdata <= rdata;
    s_apb_pready <= '1' when phase = FINISH else '0';

end architecture rtl;
