library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Asynchronous FIFO.
--
-- Moves words from the write clock domain to the read clock domain. Each side
-- keeps a binary pointer for addressing and a Gray-coded copy that crosses to
-- the other domain through a two-flop synchroniser, so only one bit changes at
-- a time and a pointer is never sampled half-updated.
--
-- Depth is 2**DEPTH_LOG2 words. Full and empty are conservative: they may
-- assert a cycle or two late after the opposite side moves, never early.
entity async_fifo is
    generic (
        -- Width of one stored word in bits (default matches full_pkg::SAMPLE_W).
        WIDTH      : positive := 12;
        -- Base-2 logarithm of the number of words stored.
        DEPTH_LOG2 : positive := 4
    );
    port (
        -- Write-side clock.
        wr_clk   : in  std_logic;
        -- Write-side asynchronous active-low reset.
        wr_rst_n : in  std_logic;
        -- Write strobe; ignored while wr_full is high.
        wr_en    : in  std_logic;
        -- Word to store.
        wr_data  : in  std_logic_vector(WIDTH - 1 downto 0);
        -- High when no further word can be accepted.
        wr_full  : out std_logic;
        -- Read-side clock.
        rd_clk   : in  std_logic;
        -- Read-side asynchronous active-low reset.
        rd_rst_n : in  std_logic;
        -- Read strobe; ignored while rd_empty is high.
        rd_en    : in  std_logic;
        -- Oldest stored word, valid while rd_empty is low.
        rd_data  : out std_logic_vector(WIDTH - 1 downto 0);
        -- High when there is nothing to read.
        rd_empty : out std_logic
    );
end entity async_fifo;

architecture rtl of async_fifo is
    constant PTR_BITS : positive := DEPTH_LOG2 + 1;

    type t_mem is array (0 to 2 ** DEPTH_LOG2 - 1) of std_logic_vector(WIDTH - 1 downto 0);
    signal mem : t_mem;

    -- Write domain: binary and Gray write pointers, then the read pointer
    -- as seen through its synchroniser.
    signal wptr_bin   : unsigned(PTR_BITS - 1 downto 0) := (others => '0');
    signal wptr_gray  : std_logic_vector(PTR_BITS - 1 downto 0) := (others => '0');
    signal rptr_meta  : std_logic_vector(PTR_BITS - 1 downto 0) := (others => '0');
    signal rptr_wsync : std_logic_vector(PTR_BITS - 1 downto 0) := (others => '0');

    -- Read domain: the mirror image.
    signal rptr_bin   : unsigned(PTR_BITS - 1 downto 0) := (others => '0');
    signal rptr_gray  : std_logic_vector(PTR_BITS - 1 downto 0) := (others => '0');
    signal wptr_meta  : std_logic_vector(PTR_BITS - 1 downto 0) := (others => '0');
    signal wptr_rsync : std_logic_vector(PTR_BITS - 1 downto 0) := (others => '0');

    signal wfull  : std_logic;
    signal rempty : std_logic;

    function to_gray(b : unsigned) return std_logic_vector is
    begin
        return std_logic_vector(b xor shift_right(b, 1));
    end function to_gray;
begin

    -- p_wr_ptr: Stores a word and advances the write pointer.
    p_wr_ptr : process(wr_clk, wr_rst_n) is
        variable next_bin : unsigned(PTR_BITS - 1 downto 0);
    begin
        if wr_rst_n = '0' then
            wptr_bin  <= (others => '0');
            wptr_gray <= (others => '0');
        elsif rising_edge(wr_clk) then
            next_bin := wptr_bin;
            if wr_en = '1' and wfull = '0' then
                mem(to_integer(wptr_bin(DEPTH_LOG2 - 1 downto 0))) <= wr_data;
                next_bin := wptr_bin + 1;
            end if;
            wptr_bin  <= next_bin;
            wptr_gray <= to_gray(next_bin);
        end if;
    end process p_wr_ptr;

    -- p_rptr_sync: Brings the read pointer into the write domain.
    p_rptr_sync : process(wr_clk, wr_rst_n) is
    begin
        if wr_rst_n = '0' then
            rptr_meta  <= (others => '0');
            rptr_wsync <= (others => '0');
        elsif rising_edge(wr_clk) then
            rptr_meta  <= rptr_gray;
            rptr_wsync <= rptr_meta;
        end if;
    end process p_rptr_sync;

    -- p_rd_ptr: Advances the read pointer after a word is taken.
    p_rd_ptr : process(rd_clk, rd_rst_n) is
        variable next_bin : unsigned(PTR_BITS - 1 downto 0);
    begin
        if rd_rst_n = '0' then
            rptr_bin  <= (others => '0');
            rptr_gray <= (others => '0');
        elsif rising_edge(rd_clk) then
            next_bin := rptr_bin;
            if rd_en = '1' and rempty = '0' then
                next_bin := rptr_bin + 1;
            end if;
            rptr_bin  <= next_bin;
            rptr_gray <= to_gray(next_bin);
        end if;
    end process p_rd_ptr;

    -- p_wptr_sync: Brings the write pointer into the read domain.
    p_wptr_sync : process(rd_clk, rd_rst_n) is
    begin
        if rd_rst_n = '0' then
            wptr_meta  <= (others => '0');
            wptr_rsync <= (others => '0');
        elsif rising_edge(rd_clk) then
            wptr_meta  <= wptr_gray;
            wptr_rsync <= wptr_meta;
        end if;
    end process p_wptr_sync;

    -- Full: the write Gray pointer equals the synchronised read pointer with
    -- its two top bits inverted.
    wfull <= '1' when wptr_gray = (not rptr_wsync(PTR_BITS - 1 downto PTR_BITS - 2)
                                   & rptr_wsync(PTR_BITS - 3 downto 0)) else '0';
    -- Empty: both Gray pointers are equal.
    rempty <= '1' when rptr_gray = wptr_rsync else '0';

    rd_data  <= mem(to_integer(rptr_bin(DEPTH_LOG2 - 1 downto 0)));
    wr_full  <= wfull;
    rd_empty <= rempty;

end architecture rtl;
