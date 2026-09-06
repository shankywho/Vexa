export type GraphNodeType =
  | 'vendor'
  | 'invoice'
  | 'purchase_order'
  | 'goods_receipt'
  | 'payment'
  | 'bank_account'
  | 'gl_account'
  | 'contract';

export type GraphEdgeType =
  | 'BILLED_ON'
  | 'RECEIVED_FOR'
  | 'PAID_BY'
  | 'POSTED_TO'
  | 'SUPPLIED_BY'
  | 'GOVERNED_BY';

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  record_id?: string;
  amount?: string;
  currency?: string;
  status?: string;
  pagerank_score?: number;
  properties?: Record<string, unknown>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  label: string;
  weight?: number;
}

export interface FinancialEvidenceGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  exception_id?: string;
}
