library ieee;
use ieee.std_logic_1164.all;

-- Reset synchroniser.
--
-- Takes an asynchronous active-low reset and delivers it to one clock domain:
-- assertion is immediate, release is held until STAGES rising clock edges have
-- passed, so every flop in the domain leaves reset on the same edge.
--
-- .. mermaid::
--    :caption: Reset release
--
--    sequenceDiagram
--      participant P as Power-on / button
--      participant S as reset_sync
--      participant D as Domain logic
--      P->>S: arst_n falls
--      S->>D: srst_n falls (no clock needed)
--      P->>S: arst_n rises
--      Note over S: STAGES clock edges
--      S->>D: srst_n rises (clock aligned)
entity reset_sync is
    generic (
        -- Number of flip-flop stages in the release chain (2 or more).
        STAGES : positive := 2
    );
    port (
        -- Clock of the domain the reset is delivered to.
        clk    : in  std_logic;
        -- Asynchronous active-low reset input.
        arst_n : in  std_logic;
        -- Active-low reset, asserted asynchronously and released synchronously.
        srst_n : out std_logic
    );
end entity reset_sync;

architecture rtl of reset_sync is
    -- Release chain, all cleared while arst_n is low.
    signal chain : std_logic_vector(STAGES - 1 downto 0) := (others => '0');
begin

    -- p_chain: Shifts a one through the chain once the reset is released.
    p_chain : process(clk, arst_n) is
    begin
        if arst_n = '0' then
            chain <= (others => '0');
        elsif rising_edge(clk) then
            chain <= chain(STAGES - 2 downto 0) & '1';
        end if;
    end process p_chain;

    srst_n <= chain(STAGES - 1);

end architecture rtl;
