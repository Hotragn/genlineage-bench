CREATE TABLE invoices (
  id INTEGER NOT NULL,
  customer TEXT NOT NULL,
  total NUMERIC NOT NULL,
  paid BOOLEAN NOT NULL,
  paid_at TIMESTAMP,
  note TEXT
);
