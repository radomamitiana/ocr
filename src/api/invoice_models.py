"""
Modèles Pydantic pour les DTOs Invoice basés sur les DTOs Java
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import date
from decimal import Decimal
from uuid import UUID
from enum import Enum


class PaymentStatus(str, Enum):
    """Statut de paiement de la facture"""
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    DRAFT = "DRAFT"


class StateValidationDTO(BaseModel):
    """DTO pour StateValidation basé sur StateValidation.java"""
    id: Optional[UUID] = None
    level: Optional[int] = None
    comment: Optional[str] = None
    validated_by: Optional[str] = Field(None, alias="validatedBy")
    validation_date: Optional[date] = Field(None, alias="validationDate")
    user_role: Optional[str] = Field(None, alias="userRole")
    sign_for_other: Optional[bool] = Field(None, alias="signForOther")
    state: Optional[bool] = None

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True  # Backward compatibility


class InvoiceGoalDTO(BaseModel):
    """DTO pour InvoiceGoal basé sur InvoiceGoal.java"""
    id: Optional[UUID] = None
    goal_id: Optional[UUID] = Field(None, alias="goalId")
    post_id: Optional[UUID] = Field(None, alias="postId")
    goal_account_number: Optional[int] = Field(None, alias="goalAccountNumber")
    post_account_number: Optional[int] = Field(None, alias="postAccountNumber")
    amount: Optional[Decimal] = None
    invoice_id: Optional[UUID] = Field(None, alias="invoiceId")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True  # Backward compatibility


class InvoiceDTO(BaseModel):
    """DTO pour Invoice basé sur Invoice.java"""
    id: Optional[UUID] = None
    invoice_number: Optional[str] = Field(None, alias="invoiceNumber")
    invoice_date: Optional[date] = Field(None, alias="invoiceDate")
    company_erp_code: Optional[str] = Field(None, alias="companyErpCode")
    supplier_name: Optional[str] = Field(None, alias="supplierName")
    excluding_taxes: Optional[Decimal] = Field(None, alias="excludingTaxes")
    vat: Optional[Decimal] = None
    including_taxes: Optional[Decimal] = Field(None, alias="includingTaxes")
    payment_state: Optional[PaymentStatus] = Field(None, alias="paymentState")
    currency_code: Optional[str] = Field(default="EUR", alias="currencyCode")
    completed: Optional[bool] = None
    draft: Optional[bool] = True
    state_validations: List[StateValidationDTO] = Field(default_factory=list, alias="stateValidations")
    invoice_goals: List[InvoiceGoalDTO] = Field(default_factory=list, alias="invoiceGoals")
    document_urls: List[str] = Field(default_factory=list, alias="documentUrls")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True  # Backward compatibility
        use_enum_values = True


class InvoiceResponse(BaseModel):
    """Réponse de l'API pour le traitement d'une facture"""
    status: str = "success"
    processing_time: float
    invoice: InvoiceDTO
