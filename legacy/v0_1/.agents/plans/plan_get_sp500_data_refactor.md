# Review
integration/clients/market_data/yfinance_data_client.py:get_sp500_data.

## Key findings

### 1. Performance risk: serial market-cap fetch for ~500 symbols

This block performs one yfinance fast_info request per symbol sequentially:

for symbol in close_prices.columns:
    market_caps[symbol] = await asyncio.to_thread(
        get_market_cap,
        symbol,
    )

That can make the method very slow and fragile. For S&P 500, this may trigger hundreds of network calls after the initial bulk price download.

Recommended fix:

- avoid per-symbol market-cap calls if possible
- use equal-weight fallback by default, or
- fetch market caps concurrently with a capped semaphore, or
- move market-cap enrichment into a cached provider/service layer

———

### 2. Data quality issue: all-NaN symbol columns are not removed

This line removes only rows where all symbols are NaN:

close_prices = close_prices.dropna(how="all")

But symbol columns with no usable data may remain. Those columns can still receive market-cap weights, which can distort the synthetic index.

Recommended fix:

close_prices = close_prices.dropna(axis=1, how="all").dropna(how="all")

Then align high_prices and low_prices to both index and columns.

———

### 3. Potential return-bias issue from missing symbol returns

This calculation does not renormalize weights for available returns on each day:

weighted_returns = daily_returns.mul(
    cap_weights,
    axis=1,
).sum(
    axis=1,
    min_count=1,
)

If some constituents are missing returns, their weight silently drops out instead of being redistributed among available constituents. That can dampen the synthetic index return.

Recommended fix:

- multiply by weights
- calculate daily sum of weights for symbols with available returns
- divide weighted return by available weight sum

———

### 4. pct_change() should explicitly disable implicit fill

Current:

daily_returns = close_prices.pct_change()

Depending on pandas version, implicit fill behavior can create misleading returns across missing values or raise warnings.

Recommended:

daily_returns = close_prices.pct_change(fill_method=None)

———

### 5. Missing test coverage

I did not find tests directly covering get_sp500_data.

Recommended tests should mock:

- pd.read_html
- yf.download
- yf.Ticker(...).fast_info

Important scenarios:

- normal multi-symbol data
- missing symbol data
- all-NaN symbol columns
- no market caps available
- partial market caps available
- no returned market data
- no usable close prices
- required output columns present
