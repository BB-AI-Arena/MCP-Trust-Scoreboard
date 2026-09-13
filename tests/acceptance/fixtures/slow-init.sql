-- Reproduce the temporary socket-only server window. Dependencies must wait
-- for the final TCP server, not start during this disposable initialization.
SELECT pg_sleep(4);
