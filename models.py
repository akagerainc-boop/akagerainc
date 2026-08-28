from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Numeric,
    ForeignKey, JSON, LargeBinary, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


# ============================================================
#  CORE: users / auth
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    google_id = Column(String(255), unique=True, index=True)
    profile_picture = Column(String(500))

    # Phase 1 additions
    password_hash = Column(String(255))
    role = Column(String(40), default="customer", index=True)  # customer|staff|developer|support|content_manager|admin|super_admin
    phone = Column(String(50))
    company = Column(String(255))
    country = Column(String(100))
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    provider = Column(String(40), default="password")  # password|google
    last_login_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    licenses = relationship("License", back_populates="user", cascade="all, delete-orphan")
    business_tokens = relationship("BusinessToken", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


# ============================================================
#  PRODUCTS  (table stays `apps` for backward compatibility)
# ============================================================
class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    description = Column(Text)
    short_description = Column(String(500))
    features = Column(JSON)
    how_it_works = Column(Text)
    installation_steps = Column(JSON)
    requires_license = Column(Boolean, default=False)
    download_url = Column(String(500))
    app_icon = Column(String(500))
    app_logo = Column(String(500))
    app_image = Column(String(500))

    # Phase 1 additions
    category = Column(String(100), index=True)
    status = Column(String(30), default="published", index=True)  # draft|published
    version = Column(String(50))
    release_date = Column(Date)
    platforms = Column(JSON)                # ["android","ios","windows","macos","web","cloud"]
    pricing_model = Column(String(30), default="free")  # free|paid|subscription
    price = Column(Numeric(10, 2), default=0)
    subscription_options = Column(JSON)     # [{plan,price,billing_period}]
    play_store_url = Column(String(500))
    app_store_url = Column(String(500))
    website_url = Column(String(500))
    documentation_url = Column(String(500))
    screenshots = Column(JSON)              # ["uploads/..."]
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    licenses = relationship("License", back_populates="app", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="app", cascade="all, delete-orphan")
    downloads = relationship("Download", back_populates="product", cascade="all, delete-orphan")


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    platform = Column(String(30), index=True)   # android|ios|windows|macos|linux|web
    label = Column(String(120))
    file_path = Column(String(500))
    external_url = Column(String(500))
    version = Column(String(50))
    architecture = Column(String(50))           # x64|arm64|universal
    file_size = Column(String(50))
    min_os = Column(String(80))
    release_notes = Column(Text)
    is_active = Column(Boolean, default=True)
    released_at = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("App", back_populates="downloads")


# ============================================================
#  SERVICES  +  dynamic purchase fields
# ============================================================
class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    description = Column(Text)
    short_description = Column(String(500))
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(8), default="USD")
    icon = Column(String(100))
    image_url = Column(String(500))
    service_type = Column(String(50), default="app_license")
    category = Column(String(100), index=True)

    # duration model
    duration_value = Column(Integer)
    duration_unit = Column(String(20))    # hour|day|week|month|year|lifetime|one_time|custom
    duration_label = Column(String(120))

    features = Column(JSON)
    requirements = Column(JSON)
    process_steps = Column(JSON)
    faqs = Column(JSON)
    terms = Column(Text)
    delivery_method = Column(String(120))
    status = Column(String(30), default="published", index=True)
    availability = Column(String(30), default="available")
    is_featured = Column(Boolean, default=False)
    popular = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    # business portal grant
    grants_business_portal_access = Column(Boolean, default=False, nullable=False)
    portal_business_name = Column(String(255))
    portal_category = Column(String(100))
    portal_access_duration_days = Column(Integer, default=365)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payments = relationship("Payment", back_populates="service")
    licenses = relationship("License", back_populates="service")
    images = relationship("Image", back_populates="service", cascade="all, delete-orphan")
    business_tokens = relationship("BusinessToken", back_populates="service")
    fields = relationship("ServiceField", back_populates="service",
                          cascade="all, delete-orphan", order_by="ServiceField.sort_order")


class ServiceField(Base):
    __tablename__ = "service_fields"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), index=True)
    label = Column(String(200), nullable=False)
    field_key = Column(String(100), nullable=False)
    field_type = Column(String(30), default="text")  # text|textarea|select|number|date|email|tel|file|checkbox
    options = Column(JSON)                            # for select
    required = Column(Boolean, default=False)
    help_text = Column(String(300))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    service = relationship("Service", back_populates="fields")


# ============================================================
#  ORDERS / PAYMENTS / INVOICES
# ============================================================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_ref = Column(String(40), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status = Column(String(30), default="pending", index=True)  # pending|processing|completed|cancelled|refunded
    subtotal = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    currency = Column(String(8), default="USD")
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")
    invoices = relationship("Invoice", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    item_type = Column(String(20), default="service")   # service|product
    ref_id = Column(Integer)
    name = Column(String(255))
    unit_amount = Column(Numeric(10, 2), default=0)
    quantity = Column(Integer, default=1)
    duration_label = Column(String(120))
    form_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(50), default="pending", index=True)  # pending|processing|completed|failed|refunded|cancelled
    payment_method = Column(String(50), default="paypal")
    provider = Column(String(40))
    provider_ref = Column(String(255))
    stripe_transaction_id = Column(String(255), unique=True)
    paypal_order_id = Column(String(255), unique=True)
    transaction_id = Column(String(255))
    service_id = Column(Integer, ForeignKey("services.id"))
    refunded_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="payments")
    service = relationship("Service", back_populates="payments")
    order = relationship("Order", back_populates="payments")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_ref = Column(String(40), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount = Column(Numeric(10, 2), default=0)
    currency = Column(String(8), default="USD")
    pdf_path = Column(String(500))
    issued_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="invoices")


# ============================================================
#  LICENSES / SUBSCRIPTIONS
# ============================================================
class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    license_key = Column(String(40), unique=True, index=True, nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"))
    app_id = Column(Integer, ForeignKey("apps.id"))
    product_id = Column(Integer)                 # mirror of app_id for spec naming
    license_type = Column(String(30), default="annual")   # trial|monthly|annual|lifetime|enterprise
    status = Column(String(30), default="active", index=True)  # active|expired|suspended|revoked
    max_devices = Column(Integer, default=1)
    is_active = Column(Boolean, default=True, index=True)
    starts_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="licenses")
    service = relationship("Service", back_populates="licenses")
    app = relationship("App", back_populates="licenses")
    activations = relationship("LicenseActivation", back_populates="license",
                               cascade="all, delete-orphan")


class LicenseActivation(Base):
    __tablename__ = "license_activations"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("licenses.id", ondelete="CASCADE"), index=True)
    device_id = Column(String(255))
    device_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    license = relationship("License", back_populates="activations")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_type = Column(String(20), default="service")  # service|product
    ref_id = Column(Integer)
    plan_name = Column(String(120))
    price = Column(Numeric(10, 2), default=0)
    currency = Column(String(8), default="USD")
    billing_period = Column(String(20), default="monthly")  # weekly|monthly|quarterly|semiannual|annual
    status = Column(String(30), default="active", index=True)  # active|cancelled|expired
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    renewal_date = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="subscriptions")


# ============================================================
#  IMAGES / MEDIA
# ============================================================
class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500))
    data = Column(LargeBinary)
    filename = Column(String(255))
    mime_type = Column(String(50), default="image/jpeg")
    alt_text = Column(String(255))
    page_type = Column(String(50), index=True)   # home|services|products|about|contact|...
    app_id = Column(Integer, ForeignKey("apps.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    app = relationship("App", back_populates="images")
    service = relationship("Service", back_populates="images")


# ============================================================
#  CONTACT / BUSINESS PORTAL
# ============================================================
class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    company = Column(String(255))
    subject = Column(String(255))
    inquiry_type = Column(String(60))
    service_required = Column(String(255))
    message = Column(Text, nullable=False)
    status = Column(String(50), default="new", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BusinessToken(Base):
    __tablename__ = "business_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True, index=True)
    business_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    token = Column(String(20), unique=True, index=True, nullable=False)
    status = Column(String(50), default="active", index=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="business_tokens")
    service = relationship("Service", back_populates="business_tokens")


# ============================================================
#  SUPPORT
# ============================================================
class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_ref = Column(String(40), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), index=True)
    name = Column(String(255))
    subject = Column(String(255), nullable=False)
    category = Column(String(80))
    priority = Column(String(20), default="normal")
    status = Column(String(30), default="open", index=True)  # open|in_progress|waiting_customer|resolved|closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("TicketMessage", back_populates="ticket",
                            cascade="all, delete-orphan", order_by="TicketMessage.created_at")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True)
    sender = Column(String(20), default="customer")  # customer|staff
    body = Column(Text, nullable=False)
    attachment_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("SupportTicket", back_populates="messages")


# ============================================================
#  CONTENT: blog / docs / faqs / testimonials / case studies / industries
# ============================================================
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(30), index=True)   # product|service|blog|case_study
    name = Column(String(120), nullable=False)
    slug = Column(String(140), index=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    excerpt = Column(String(500))
    body = Column(Text)
    cover_image = Column(String(500))
    author = Column(String(120))
    category = Column(String(100), index=True)
    tags = Column(JSON)
    status = Column(String(30), default="draft", index=True)  # draft|published
    reading_time = Column(Integer, default=3)
    is_featured = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocPage(Base):
    __tablename__ = "doc_pages"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    section = Column(String(120), index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text)
    sort_order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Faq(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), index=True)
    question = Column(String(400), nullable=False)
    answer = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Testimonial(Base):
    __tablename__ = "testimonials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    role = Column(String(160))
    company = Column(String(160))
    quote = Column(Text, nullable=False)
    avatar = Column(String(500))
    rating = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CaseStudy(Base):
    __tablename__ = "case_studies"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    client = Column(String(200))
    category = Column(String(100), index=True)
    summary = Column(String(500))
    challenge = Column(Text)
    solution = Column(Text)
    results = Column(Text)
    technologies = Column(JSON)
    platforms = Column(JSON)
    screenshots = Column(JSON)
    cover_image = Column(String(500))
    link = Column(String(500))
    is_featured = Column(Boolean, default=False)
    status = Column(String(30), default="published", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Industry(Base):
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    name = Column(String(160), nullable=False)
    icon = Column(String(80))
    summary = Column(String(500))
    body = Column(Text)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


# ============================================================
#  CAREERS / INTERNSHIPS
# ============================================================
class Internship(Base):
    __tablename__ = "internships"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(200), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(120), index=True)
    description = Column(Text)
    requirements = Column(JSON)
    duration_label = Column(String(120))
    start_date = Column(Date)
    end_date = Column(Date)
    price = Column(Numeric(10, 2), default=0)
    is_free = Column(Boolean, default=True)
    positions = Column(Integer, default=1)
    deadline = Column(Date)
    status = Column(String(30), default="open", index=True)  # open|closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    applications = relationship("InternshipApplication", back_populates="internship",
                               cascade="all, delete-orphan")


class InternshipApplication(Base):
    __tablename__ = "internship_applications"

    id = Column(Integer, primary_key=True, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id", ondelete="CASCADE"), index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    education = Column(String(300))
    interest_area = Column(String(160))
    cv_path = Column(String(500))
    preferred_duration = Column(String(120))
    start_date = Column(Date)
    message = Column(Text)
    status = Column(String(30), default="submitted", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    internship = relationship("Internship", back_populates="applications")


class JobPosition(Base):
    __tablename__ = "job_positions"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(200), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(120), index=True)
    location = Column(String(160))
    employment_type = Column(String(60))
    description = Column(Text)
    responsibilities = Column(JSON)
    requirements = Column(JSON)
    benefits = Column(JSON)
    status = Column(String(30), default="open", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    applications = relationship("JobApplication", back_populates="job",
                               cascade="all, delete-orphan")


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_positions.id", ondelete="CASCADE"), index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    resume_path = Column(String(500))
    cover_letter = Column(Text)
    status = Column(String(30), default="submitted", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("JobPosition", back_populates="applications")


# ============================================================
#  NOTIFICATIONS / NAVIGATION / AUDIT / SITE CONTENT
# ============================================================
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type = Column(String(60))
    title = Column(String(255))
    body = Column(Text)
    link = Column(String(500))
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


class NavigationItem(Base):
    __tablename__ = "navigation_items"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("navigation_items.id", ondelete="CASCADE"), index=True)
    location = Column(String(30), default="header", index=True)  # header|footer
    label = Column(String(120), nullable=False)
    url = Column(String(300))
    column_group = Column(String(80))     # footer column heading / mega-menu group
    sort_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)

    children = relationship("NavigationItem", backref="parent", remote_side=[id],
                            single_parent=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_email = Column(String(255), index=True)
    action = Column(String(80))
    entity = Column(String(80), index=True)
    entity_id = Column(String(80))
    meta = Column(JSON)
    ip = Column(String(80))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    code_hash = Column(String(255), nullable=False)
    purpose = Column(String(30), default="login", index=True)  # login|verify|reset
    attempts = Column(Integer, default=0)
    consumed = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SiteContent(Base):
    __tablename__ = "site_content"

    id = Column(Integer, primary_key=True, index=True)
    content_key = Column(String(100), unique=True, index=True, nullable=False)
    content_value = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


Index("ix_downloads_product_platform", Download.product_id, Download.platform)
Index("ix_images_page_active", Image.page_type, Image.is_active)
