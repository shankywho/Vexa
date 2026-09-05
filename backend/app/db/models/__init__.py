"""ORM models package.

Importing this package registers every model with the SQLAlchemy registry,
so ``Base.metadata`` is complete for ``create_all`` and Alembic autogenerate.
"""

from app.db.base import Base
from app.db.models.agent import AgentRun, AgentStep
from app.db.models.audit import (
    AgentPromptVersion,
    AuditEvent,
    PolicyVersion,
)
from app.db.models.banking import BankAccount, BankTransaction, Payment
from app.db.models.close_run import CloseRun, CloseTask
from app.db.models.counterparty import Customer, Vendor
from app.db.models.exception import (
    ExceptionAction,
    ExceptionEvidence,
    ExceptionRecord,
    ReconciliationMatch,
    ReconciliationResult,
    ReversalAction,
)
from app.db.models.fx import FxRate
from app.db.models.ledger import JournalEntry, JournalEntryLine, LedgerAccount
from app.db.models.procurement import (
    Contract,
    ExpenseReport,
    GoodsReceipt,
    GoodsReceiptLine,
    Invoice,
    InvoiceLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.db.models.tenancy import Company, RoleAssignment, User

__all__ = [
    "AgentPromptVersion",
    "AgentRun",
    "AgentStep",
    "AuditEvent",
    "BankAccount",
    "BankTransaction",
    "Base",
    "CloseRun",
    "CloseTask",
    "Company",
    "Contract",
    "Customer",
    "ExceptionAction",
    "ExceptionEvidence",
    "ExceptionRecord",
    "ExpenseReport",
    "FxRate",
    "GoodsReceipt",
    "GoodsReceiptLine",
    "Invoice",
    "InvoiceLine",
    "JournalEntry",
    "JournalEntryLine",
    "LedgerAccount",
    "Payment",
    "PolicyVersion",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "ReconciliationMatch",
    "ReconciliationResult",
    "ReversalAction",
    "RoleAssignment",
    "User",
    "Vendor",
]
