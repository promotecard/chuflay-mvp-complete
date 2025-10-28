-- Seeds de ejemplo
INSERT INTO users (email, name) VALUES ('alice@example.com', 'Alice') ON CONFLICT DO NOTHING;
INSERT INTO users (email, name) VALUES ('bob@example.com', 'Bob') ON CONFLICT DO NOTHING;
