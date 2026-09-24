# Python + SQL feeder analytics

**Live logging is now available:** see [LIVE.md](LIVE.md) for the separate LIVE
SQLite database, continuous collector, status command and SQL examples. The
demo and documentation below describe the original simulated-data pipeline.

This independent, offline addition records **SIMULATED** feeder samples in a SQLite SQL database and measures command-to-position-feedback response times. Python's standard library is sufficient. It does not connect to or write to CODESYS or Ignition. Seeq is not required or integrated yet.

From the project root, using Python 3.10 or newer:

```powershell
python analytics/feeder_lab.py demo
python -m unittest discover -s analytics -p 'test_*.py' -v
```

Open `analytics/output/report.html` in a browser. The report includes response bars, summary counts, an outcome filter, UTC event history, and a JSON download. The database is `analytics/output/feeder.sqlite3`. Running the demo again appends a separate run; the report shows the latest generated run. Use `--output <directory>` for a separate database/report set.

## Data and interpretation

`schema.sql` defines runs, coherent timestamped samples, derived operations and a summary view. Timestamps are UTC Unix milliseconds; feeder and run IDs isolate separate streams. The current sample columns map to `Cmd_CB_Close`, `Cmd_CB_Open`, and `Sts_CB_Open`; quality is GOOD only when all three signals are good. The future collector must use actual browsed node paths and preserve quality and acquisition timing.

The synthetic fixture has 100 close requests, including five slow responses (12, 29, 47, 68, 91), two absent responses (35, 80), and two bad-quality intervals (55, 95). Successful simulated closes are followed by open requests: 98 opens, 198 requests total. The simulator provides automatic position changes only in this database fixture; the actual PLC's feedback remains manual.

The analyzer measures a request rising edge to the first target feedback, provided acquisition remains continuous and good. Its illustrative limits are 500 ms for slow response, 2,000 ms for missing feedback, and a maximum 150 ms between samples. The sample cadence is 100 ms. Values are recorded at observation times, so measured response time includes sampling uncertainty. These are not manufacturer limits or mechanical travel-time measurements.

Outcomes:

- NORMAL / SLOW: target feedback observed by the deadline, with slow meaning strictly greater than 500 ms.
- NO_FEEDBACK: target not observed through the deadline. This can include a blocked request; it is not proof of equipment failure.
- UNKNOWN_DATA: bad quality or a sampling gap interrupted the measurement.
- UNKNOWN_START: a high command was observed without a known preceding low value.
- INCOMPLETE: recording ended before the response window was resolved.
- SUPERSEDED: another request arrived before the outstanding request resolved.
- ALREADY_AT_TARGET / CONFLICTING_COMMANDS: request cannot yield a meaningful response-time measurement.

The existing PLC has only an open-position bit. A false value is not independent closed-contact confirmation. The analyzer does not infer protection trips, availability, or lockout durations from this limited data. Those need additional signals and explicit definitions.

## SQL examples

Run these through Python's `sqlite3` module or any SQLite client:

```sql
SELECT * FROM operation_summary WHERE run_id = (SELECT MAX(id) FROM runs);

SELECT feeder, command_ms, direction, response_ms, outcome
FROM operations
WHERE run_id = (SELECT MAX(id) FROM runs) AND outcome <> 'NORMAL'
ORDER BY command_ms;

SELECT timestamp_ms, quality, cmd_close, cmd_open, cb_open
FROM samples WHERE run_id = (SELECT MAX(id) FROM runs)
ORDER BY feeder, timestamp_ms;
```

## Live integration

The separate LIVE pipeline is implemented in `live_logger.py` and `live_report.py`;
see [LIVE.md](LIVE.md). It preserves quality, source timestamps and acquisition
gaps and reads actual lab observations. Its one-second cadence cannot support
the simulated fixture's sub-second classifications. Protection-trip analytics
require a documented trip indication. SQLite is a local lab event store, not an
Ignition historian schema or a verified Seeq connector. Seeq remains future work.
