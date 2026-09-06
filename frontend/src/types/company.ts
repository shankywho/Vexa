export interface Company {
  id: string;
  name: string;
  legal_name?: string;
  tax_id?: string;
  base_currency: string;
  fiscal_year_end: string;
  created_at?: string;
  active_close_runs?: number;
  total_transactions?: number;
}
