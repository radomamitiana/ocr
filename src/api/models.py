"""
Modèles Pydantic pour l'API REST
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PROCESSING = "processing"


class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class Contact(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None


class Supplier(BaseModel):
    name: Optional[str] = None
    address: Optional[Address] = None
    siret: Optional[str] = None
    vat_number: Optional[str] = None
    contact: Optional[Contact] = None


class Customer(BaseModel):
    name: Optional[str] = None
    address: Optional[Address] = None
    customer_id: Optional[str] = None


class Invoice(BaseModel):
    number: Optional[str] = None
    date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = "EUR"
    payment_terms: Optional[str] = None


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    vat_rate: Optional[float] = None
    amount_excl_vat: Optional[float] = None
    vat_amount: Optional[float] = None
    amount_incl_vat: Optional[float] = None


class Totals(BaseModel):
    subtotal_excl_vat: Optional[float] = None
    total_vat: Optional[float] = None
    total_incl_vat: Optional[float] = None
    amount_due: Optional[float] = None


class Validation(BaseModel):
    calculation_check: bool = False
    required_fields_present: bool = False
    data_quality_score: float = 0.0


class Metadata(BaseModel):
    filename: str
    processing_date: datetime = Field(default_factory=datetime.now)
    confidence_score: float = 0.0
    processing_time: float = 0.0


class InvoiceData(BaseModel):
    metadata: Metadata
    supplier: Optional[Supplier] = None
    customer: Optional[Customer] = None
    invoice: Optional[Invoice] = None
    line_items: List[LineItem] = []
    totals: Optional[Totals] = None
    validation: Optional[Validation] = None


class ProcessingOptions(BaseModel):
    language: str = "fra"
    confidence_threshold: float = 0.8
    enable_validation: bool = True


class ProcessInvoiceResponse(BaseModel):
    status: ProcessingStatus
    processing_time: float
    data: Optional[InvoiceData] = None


class ErrorResponse(BaseModel):
    status: ProcessingStatus = ProcessingStatus.ERROR
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)


class VersionResponse(BaseModel):
    version: str = "1.0.0"
    api_version: str = "v1"
    build_date: str = "2025-08-19"
