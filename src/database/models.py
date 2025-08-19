"""
Modèles SQLAlchemy basés sur les entités Java existantes - Version complète
"""

from sqlalchemy import Column, String, Date, DateTime, Boolean, Text, ForeignKey, TIMESTAMP, NUMERIC, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .connection import Base


class Company(Base):
    """
    Modèle pour la table company basé sur CompanyEntity.java
    """
    __tablename__ = 'company'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_erp_code = Column(String(255), nullable=False, unique=True)
    company_rcs = Column(String(255))
    company_address = Column(Text)
    company_name = Column(String(255), nullable=False)
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Relations
    invoices = relationship("Invoice", back_populates="company")
    goals = relationship("Goal", back_populates="company")
    posts = relationship("Post", back_populates="company")


class Supplier(Base):
    """
    Modèle pour la table supplier basé sur SuppliersEntity.java
    """
    __tablename__ = 'supplier'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    social_reason = Column(String(255), nullable=False)
    rcs = Column(String(255))
    address = Column(Text)
    email = Column(String(255))
    phone_number = Column(String(50))
    is_active = Column(Boolean, nullable=False, default=True)
    contact_name = Column(String(255))
    goals = Column(ARRAY(Integer))
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Relations
    invoices = relationship("Invoice", back_populates="supplier")


class PrincipalAccount(Base):
    """
    Modèle pour la table principal_account basé sur PrincipalAccountEntity.java
    """
    __tablename__ = 'principal_account'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_number = Column(Integer, nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Relations
    goals = relationship("Goal", back_populates="principal_account")


# Définir Goal et Post après Company pour éviter les problèmes de dépendances
# Ces classes seront définies plus bas dans le fichier


class Invoice(Base):
    """
    Modèle pour la table invoice basé sur InvoiceEntity.java
    """
    __tablename__ = 'invoice'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(255))
    invoice_date = Column(Date, nullable=False)
    company_erp_code = Column(String(255), ForeignKey('company.company_erp_code'))
    supplier_name = Column(String(255))
    excluding_taxes = Column(NUMERIC(10, 2))
    vat = Column(NUMERIC(10, 2))
    including_taxes = Column(NUMERIC(10, 2), nullable=False)
    payment_state = Column(String(100))
    currency_code = Column(String(3), default='EUR')
    is_complete = Column(Boolean, default=False)
    is_draft = Column(Boolean, default=True)
    document_url = Column(Text)
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Clés étrangères supplémentaires pour les relations ML
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('supplier.id'))
    
    # Relations
    company = relationship("Company", back_populates="invoices")
    supplier = relationship("Supplier", back_populates="invoices")
    invoice_goals = relationship("InvoiceGoal", back_populates="invoice", cascade="all, delete-orphan")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    ml_data = relationship("InvoiceMLData", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceGoal(Base):
    """
    Modèle pour la table invoice_goal basé sur InvoiceGoalEntity.java
    """
    __tablename__ = 'invoice_goal'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey('goal.id'))
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'))
    amount = Column(NUMERIC(10, 2))
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice.id'))
    goal_account_number = Column(Integer)
    post_account_number = Column(Integer)
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Relations
    invoice = relationship("Invoice", back_populates="invoice_goals")
    goal = relationship("Goal", back_populates="invoice_goals")
    post = relationship("Post", back_populates="invoice_goals")


# Tables supplémentaires pour le ML et l'amélioration des données
class InvoiceLineItem(Base):
    """
    Table pour stocker les lignes de facture (pour le ML)
    """
    __tablename__ = 'invoice_line_item'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice.id'))
    line_number = Column(Integer, nullable=False)
    description = Column(Text)
    quantity = Column(NUMERIC(10, 3))
    unit_price = Column(NUMERIC(10, 2))
    vat_rate = Column(NUMERIC(5, 4))
    amount_excl_vat = Column(NUMERIC(10, 2))
    vat_amount = Column(NUMERIC(10, 2))
    amount_incl_vat = Column(NUMERIC(10, 2))
    created_date = Column(TIMESTAMP, server_default=func.now())
    
    # Relations
    invoice = relationship("Invoice", back_populates="line_items")


class InvoiceMLData(Base):
    """
    Table pour stocker les données ML et améliorer l'extraction
    """
    __tablename__ = 'invoice_ml_data'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice.id'))
    raw_text = Column(Text)  # Texte OCR brut
    extracted_data = Column(Text)  # Données extraites en JSON
    confidence_score = Column(NUMERIC(3, 2))
    processing_time = Column(NUMERIC(10, 3))
    validation_score = Column(NUMERIC(3, 2))
    data_quality_score = Column(NUMERIC(3, 2))
    confidence_threshold = Column(NUMERIC(3, 2), default=0.8)
    created_date = Column(TIMESTAMP, server_default=func.now())
    
    # Relations
    invoice = relationship("Invoice", back_populates="ml_data")


# Tables supplémentaires si nécessaire (GCA, StateValidation, etc.)
class Gca(Base):
    """
    Modèle pour la table gca (si nécessaire)
    """
    __tablename__ = 'gca'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Ajouter les champs selon GcaEntity.java si nécessaire
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))


class StateValidation(Base):
    """
    Modèle pour la table state_validation (si nécessaire)
    """
    __tablename__ = 'state_validation'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Ajouter les champs selon StateValidationEntity.java si nécessaire
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))


# Définition des classes Goal et Post à la fin pour éviter les dépendances circulaires
class Goal(Base):
    """
    Modèle pour la table goal basé sur GoalEntity.java
    """
    __tablename__ = 'goal'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_number = Column(Integer, nullable=False)
    description = Column(String(255))
    year = Column(Integer, nullable=False)
    budget_charges = Column(NUMERIC(15, 2))
    budget_incomes = Column(NUMERIC(15, 2))
    principal_account_id = Column(UUID(as_uuid=True), ForeignKey('principal_account.id'))
    principal_account_number = Column(Integer)
    company_erp_code = Column(String(255), ForeignKey('company.company_erp_code'))
    is_active = Column(Boolean, nullable=False, default=True)
    is_closed = Column(Boolean, nullable=False, default=False)
    charges = Column(NUMERIC(15, 2))
    incomes = Column(NUMERIC(15, 2))
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Relations
    company = relationship("Company", back_populates="goals")
    principal_account = relationship("PrincipalAccount", back_populates="goals")
    posts = relationship("Post", back_populates="goal")
    invoice_goals = relationship("InvoiceGoal", back_populates="goal")


class Post(Base):
    """
    Modèle pour la table post basé sur PostEntity.java
    """
    __tablename__ = 'post'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_number = Column(Integer, nullable=False)
    description = Column(String(255))
    year = Column(Integer, nullable=False)
    budget_charges = Column(NUMERIC(15, 2))
    budget_incomes = Column(NUMERIC(15, 2))
    goal_id = Column(UUID(as_uuid=True), ForeignKey('goal.id'), nullable=False)
    goal_number = Column(Integer)
    company_erp_code = Column(String(255), ForeignKey('company.company_erp_code'), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_closed = Column(Boolean, nullable=False, default=False)
    charges = Column(NUMERIC(15, 2))
    incomes = Column(NUMERIC(15, 2))
    created_date = Column(TIMESTAMP, server_default=func.now())
    last_modified_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Relations
    company = relationship("Company", back_populates="posts")
    goal = relationship("Goal", back_populates="posts")
    invoice_goals = relationship("InvoiceGoal", back_populates="post")
