CREATE INDEX IF NOT EXISTS idx_analysis_results_action
ON analysis_results(action);

CREATE INDEX IF NOT EXISTS idx_analysis_results_created_at
ON analysis_results(created_at);