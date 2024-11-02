--------------------------------------------------------------------------------
-- Copyright (C) 2023 Macallyster Edmondson
--------------------------------------------------------------------------------
-- This program is free software: you can redistribute it and/or modify it under
-- the terms of the GNU General Public License as published by the Free Software
-- Foundation, either version 3 of the License, or (at your option) any later
-- version.
--
-- This program is distributed in the hope that it will be useful, but WITHOUT
-- ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
-- FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License along with
-- this program. If not, see <https://www.gnu.org/licenses/>.
--------------------------------------------------------------------------------
-- Descritpiton:
--  TODO: Add description
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
-- Entity Declaration
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity static_uart_tx is
  generic
  (
    SYS_CLK_HZ : natural := 125_000_000; -- System Clock Frequency in MHz
    -- UART Classification
    BAUD_RATE 	      : integer; -- in bps (uart baud is 1 bit)
    DATA_BITS_WIDTH 	: integer range 5 to 9 := 8;
    PARITY_MODE       : string := "none"; -- "even", "odd", or "none"
    STOP_BITS_WIDTH   : integer range 1 to 2 := 1
  );
  port
  (
    -- Synchronous interface
    clk 	: in std_logic;
    reset : in std_logic;
    -- Slave interface
    in_data  : in  std_logic_vector(DATA_BITS_WIDTH-1 downto 0);
    in_valid : in  std_logic;
    in_ready : out std_logic;
    -- UART output interface
    out_tx : out std_logic
  );
end static_uart_tx;

--------------------------------------------------------------------------------
-- Package Declaration
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

package static_uart_tx_pkg is
  component static_uart_tx is
    generic
    (
      SYS_CLK_MHZ : real range 0.0 to real'high := 125.0;
      BAUD_RATE 	      : integer;
      DATA_BITS_WIDTH 	: integer range 5 to 9 := 8;
      PARITY_MODE       : string := "none";
      STOP_BITS_WIDTH   : integer range 1 to 2 := 1
    );
    port
    (
      clk 	: in std_logic;
      reset : in std_logic;
      in_data  : in  std_logic_vector(DATA_BITS_WIDTH-1 downto 0);
      in_valid : in  std_logic;
      in_ready : out std_logic;
      out_tx : out std_logic
    );
  end component static_uart_tx;
end package; -- static_uart_tx_pkg


--------------------------------------------------------------------------------
-- Architecture Definition (rtl)
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_misc.all;
use ieee.math_real.all;
use ieee.numeric_std.all;

architecture rtl of static_uart_tx is

  ------------------------------------------------------------------------------
  -- Constant Calculation Functions
  ------------------------------------------------------------------------------
  function PARITY_BITS_WIDTH return integer is
  begin
    if PARITY_MODE = "none" then
      return 0;
    else
      return 1;
    end if;
  end function;

  ------------------------------------------------------------------------------
  -- Constants
  ------------------------------------------------------------------------------
  -- Width of data to be serialized on the wire
  constant OUT_DATA_WIDTH     : integer := DATA_BITS_WIDTH + PARITY_BITS_WIDTH + STOP_BITS_WIDTH + 1; -- add 1 for start_bit
  -- Calculations for baud counter
  constant BAUD_RATE_DIVISOR  : real := round(real(SYS_CLK_HZ)/real(BAUD_RATE));
  constant BAUD_CLK_HZ				: real := real(SYS_CLK_HZ)/BAUD_RATE_DIVISOR;
  constant BAUD_COUNTER_WIDTH : integer := integer(ceil(log2(BAUD_RATE_DIVISOR)));
  constant BAUD_PERCENT_DIF   : real := (BAUD_CLK_HZ - real(BAUD_RATE))/real(BAUD_RATE);

  ------------------------------------------------------------------------------
  -- State machine
  ------------------------------------------------------------------------------
  type uart_tx_state_t is (idle_read, uart_write);
  signal uart_tx_state : uart_tx_state_t;

  ------------------------------------------------------------------------------
  -- Signals
  ------------------------------------------------------------------------------
  -- `out_data` represents a SIPO shift register. Data is shifted towards 0, so 0 will be the start bit when loaded, those
  -- above it will be the data bits, followed by parity, and then stop bits.
  signal out_data : std_logic_vector(OUT_DATA_WIDTH-1 downto 0);
    alias start_bit  : std_logic
                       is out_data(0);
    alias data_bits  : std_logic_vector(DATA_BITS_WIDTH-1 downto 0)
                       is out_data(DATA_BITS_WIDTH downto 1);
    -- Aliases after this point must be used carefully as `parity_bit` is defined using a generic that could be 0.
    alias parity_bit : std_logic
                       is out_data(DATA_BITS_WIDTH+PARITY_BITS_WIDTH);
    alias stop_bits  : std_logic_vector(STOP_BITS_WIDTH-1 downto 0)
                       is out_data(DATA_BITS_WIDTH+PARITY_BITS_WIDTH+STOP_BITS_WIDTH downto DATA_BITS_WIDTH+PARITY_BITS_WIDTH+1);

  -- Clock enable pulse for baud rate output
  signal baud_clk_en : std_logic;
  signal baud_clk_counter : std_logic_vector(BAUD_COUNTER_WIDTH-1 downto 0);

begin
  -- Generic Checks
  generic_check_proc : process
    -- This process allows both synthesis tools and simulators to check assertions,
    -- while preventing simulators from constant running of contained statements each
    -- delta cycle.
  begin
    assert real(SYS_CLK_HZ) >= real(BAUD_RATE) report
        "The system clock frequency must be greater than the baud rate for baud "
        & "rate generation to work."
        severity error;


    assert PARITY_MODE = "even" or PARITY_MODE = "odd" or PARITY_MODE = "none" report
        "Unknown PARITY_MODE: '" & PARITY_MODE & "'."
        severity error;

    -- If the system clock frequncy is not twice the baud rate, one extra stop bit will be sent after each transaction
    -- before the start of new data. This is due to the extra clock cycle it takes for a ready-valid transaction to take
    -- place.
    assert real(SYS_CLK_HZ) >= 2.0*real(BAUD_RATE) report
        "The system clock frequency is not at least double the baud rate. This will "
        & "cause an extra stop bit to be sent after each transaction."
        severity warning;

    -- Alert the user of large counter for baud rate generation
    assert BAUD_COUNTER_WIDTH <= 16 report
      "A " & integer'image(BAUD_COUNTER_WIDTH) & " bit counter is necessary to implement a divisior of "
      & real'image(BAUD_RATE_DIVISOR) & ". Are your design parameters correct?"
      severity warning;

    -- Ensure the baud rate is within 2% of expected
    assert BAUD_PERCENT_DIF*sign(BAUD_PERCENT_DIF) < 0.02 report
      "The generated baud rate diverges " & real'image(BAUD_PERCENT_DIF*100.0) & "% from the expected baud rate. "
      & "Actual: " & real'image(BAUD_CLK_HZ) & ";  Expected: " & real'image(real(BAUD_RATE)) & "."
      severity warning;

    wait; -- wait forever
  end process generic_check_proc;



  -- The pair of baud_div_x_gen generates accounts for potential
  -- synthesis errors if the baud rate divisor is 1
  baud_div_n1_gen: if integer(BAUD_RATE_DIVISOR) /= 1 generate
    -- Baud rate clk enable generator
    baud_clk_en_proc: process(clk) is
    begin
      if rising_edge(clk) then
        -- Clear pulsed ignals
        baud_clk_en <= '0';

        if reset = '1' then
          baud_clk_counter <= (others => '0');
        else
          -- Generate a clock enable pulse, baud_clk_en, which asserts at (System Clock)/(Baud Rate Divisior) frequency.
          if(unsigned(baud_clk_counter) = to_unsigned(integer(BAUD_RATE_DIVISOR)-1, baud_clk_counter'length)) then
            baud_clk_counter <= (others => '0');
            baud_clk_en <= '1'; -- pulsed
          else
            baud_clk_counter <= std_logic_vector(unsigned(baud_clk_counter) + 1);
          end if;
        end if; -- reset = '1'
      end if; -- rising_edge(clk)
    end process baud_clk_en_proc;
  end generate;

  baud_div_1_gen: if integer(BAUD_RATE_DIVISOR) = 1 generate
    baud_clk_en <= '1';
  end generate;


  uart_tx_state_proc: process(clk) is
    variable parity_tmp : std_logic;
  begin
    if rising_edge(clk) then
      if reset = '1' then -- synchronous reset
        in_ready <= '1';
        out_tx <= '1';
        uart_tx_state <= idle_read;
      else -- normal operation

        case uart_tx_state is
          when uart_write =>
            -- Only run the uart output logic when a baud enable pulse comes in.
            -- This is similar to a handoff to a slower, phase-aligned clock domain.
            if baud_clk_en = '1' then
              -- right shift out_data, shift zero in for stop bit check. (see below)
              out_data <= '0' & out_data(out_data'length-1 downto 1);
              out_tx <= out_data(0);

              if (or_reduce(out_data(out_data'length-1 downto 1)) = '0') and (out_data(0) = '1') then
                -- All data has been sent except the (final) stop bit. As the stop bit is always '1'
                -- we know when we are finished sending data, which is only under this condition.
                -- The stop bit will be set on the same edge this logic is run.
                -- Example for 8N1:
                  -- data_out (inital): "1      00000000      0"
                  --										 ^      ^^^^^^^^      ^
                  -- 										 stop     data    start
                  -- data_out (after 9 shifts): "0      00000000      1"
                  --                             ^      ^^^^^^^^      ^
                  --                             shifted in 0s     stop bit

                -- Set state back to idle and assert the ready bit
                uart_tx_state <= idle_read;
                in_ready <= '1';
              end if;
            end if; -- baud_clk_en = '1'
          when others => -- idle_read
             if in_valid = '1' then
              in_ready <= '0'; -- We won't be ready again until data is finished sending.
              uart_tx_state <= uart_write;

              start_bit <= '0'; -- start bit is always '0'
              data_bits <= in_data;
              stop_bits <= (others => '1'); -- stop bit(s) are always '1'

              -- Parity bit generation conditional on generic
              if PARITY_BITS_WIDTH > 0 then
                parity_tmp := xor_reduce(in_data);
                if PARITY_MODE = "even" then
                  parity_bit <= parity_tmp;
                elsif PARITY_MODE = "odd" then
                  parity_bit <= not parity_tmp;
                elsif PARITY_MODE = "none" then
                  null;
                end if;
              end if;

            end if; -- in_valid = '1'

        end case; -- uart_tx_state

      end if; -- reset = '1'
    end if; -- rising_edge(clk)
  end process uart_tx_state_proc;
end architecture rtl;
