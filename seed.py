"""
Idempotent database seeding.

Run standalone:   python seed.py
Or via API:       POST /api/admin/seed   (admin auth)
"""
import os
from datetime import datetime, date, timedelta

from database import SessionLocal, engine, Base
from models import (
    User, App, Service, ServiceField, Download, NavigationItem, SiteContent,
    Category, BlogPost, Faq, Testimonial, Industry, Internship, JobPosition, CaseStudy,
    DocPage,
)
from auth_utils import hash_password
from utils import slugify
import site_defaults as sd


def _ensure_content(db, key, value):
    row = db.query(SiteContent).filter(SiteContent.content_key == key).first()
    if not row:
        db.add(SiteContent(content_key=key, content_value=value))


def seed_site_content(db):
    for key, value in sd.DEFAULTS.items():
        _ensure_content(db, key, value)
    db.commit()


def seed_admin(db):
    email = os.getenv("ADMIN_EMAIL", "admin@akagerainc.store").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "ChangeMe#Akagera2026")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name="Akagera Admin", email=email, role="super_admin",
                    provider="password", email_verified=True, is_active=True,
                    password_hash=hash_password(password))
        db.add(user)
        print(f"  + super admin: {email}")
    else:
        user.role = "super_admin"
        if not user.password_hash:
            user.password_hash = hash_password(password)
    db.commit()


def seed_navigation(db):
    if db.query(NavigationItem).count() > 0:
        return
    order = 0
    for top in sd.HEADER_NAV:
        order += 1
        parent = NavigationItem(location="header", label=top["label"], url=top["url"],
                                sort_order=order, is_enabled=True)
        db.add(parent)
        db.flush()
        for j, child in enumerate(top.get("children", [])):
            db.add(NavigationItem(location="header", parent_id=parent.id, label=child["label"],
                                  url=child["url"], sort_order=j, is_enabled=True))
    for i, col in enumerate(sd.FOOTER_NAV):
        parent = NavigationItem(location="footer", label=col["column_group"],
                                column_group=col["column_group"], sort_order=i, is_enabled=True)
        db.add(parent)
        db.flush()
        for j, child in enumerate(col["children"]):
            db.add(NavigationItem(location="footer", parent_id=parent.id, label=child["label"],
                                  url=child["url"], column_group=col["column_group"],
                                  sort_order=j, is_enabled=True))
    db.commit()
    print("  + navigation seeded")


def seed_categories(db):
    if db.query(Category).count() > 0:
        return
    product_cats = ["Productivity", "Education", "Business", "Finance", "Communication",
                    "Security", "Utilities", "AI", "Developer Tools", "Enterprise"]
    blog_cats = ["Technology", "Software Development", "AI", "Mobile Development",
                 "Web Development", "Business", "Tutorials", "Company News"]
    for i, n in enumerate(product_cats):
        db.add(Category(kind="product", name=n, slug=slugify(n), sort_order=i))
    for i, n in enumerate(blog_cats):
        db.add(Category(kind="blog", name=n, slug=slugify(n), sort_order=i))
    db.commit()


SERVICE_SEED = [
    dict(name="Custom Mobile App Development", category="Software Development", price=1200,
         duration_value=30, duration_unit="day", service_type="system_development",
         short_description="Turn your idea into a production-ready Android and iOS application.",
         description="End-to-end mobile product engineering: discovery, UI/UX, development, QA, "
                     "store deployment, and post-launch support.",
         features=["Native or cross-platform build", "UI/UX design included", "Play Store & App Store submission",
                   "Backend & API", "30 days post-launch support"],
         requirements=["Product brief or idea document", "Brand assets (if any)", "Preferred platforms"],
         process_steps=["Discovery", "UI/UX", "Development", "Testing", "Deployment", "Maintenance"],
         delivery_method="Remote delivery + scheduled demos",
         fields=[
             ("Project name", "project_name", "text", True, None),
             ("Describe your app", "description", "textarea", True, None),
             ("Target platform", "platform", "select", True, ["Android", "iOS", "Both"]),
             ("Must-have features", "features", "textarea", False, None),
             ("Deadline", "deadline", "date", False, None),
             ("Budget range (USD)", "budget", "text", False, None),
         ]),
    dict(name="Website Development", category="Software Development", price=500,
         duration_value=14, duration_unit="day", service_type="system_development",
         short_description="A fast, responsive marketing or business website.",
         description="Design and build a modern responsive website with a content structure you can update.",
         features=["Responsive design", "SEO basics", "Contact form", "CMS handover", "Analytics setup"],
         requirements=["Content & images", "Domain access"],
         process_steps=["Brief", "Design", "Build", "Review", "Launch"],
         delivery_method="Remote delivery",
         fields=[
             ("Business name", "business_name", "text", True, None),
             ("Pages needed", "pages", "textarea", True, None),
             ("Reference websites", "references", "textarea", False, None),
         ]),
    dict(name="Professional Software License", category="Licensing", price=49,
         duration_value=1, duration_unit="year", service_type="app_license",
         short_description="A 1-year license key for a licensed Akagera product.",
         description="Purchase a license key that activates a licensed Akagera product for one year.",
         features=["1-year validity", "Priority updates", "Email support"],
         requirements=["Choose the product", "Number of devices"],
         fields=[
             ("Product", "product", "text", True, None),
             ("License type", "license_type", "select", True, ["Trial", "Monthly", "Annual", "Lifetime", "Enterprise"]),
             ("Number of devices", "devices", "number", True, None),
             ("Organization name", "organization", "text", False, None),
         ]),
    dict(name="SaaS Subscription", category="Subscriptions", price=19,
         duration_value=1, duration_unit="month", service_type="subscription",
         short_description="Monthly access to an Akagera SaaS platform.",
         description="Recurring monthly access to a cloud platform, billed each month.",
         features=["Cloud hosting", "Automatic updates", "Standard support"],
         fields=[("Workspace name", "workspace", "text", True, None),
                 ("Team size", "team_size", "number", False, None)]),
    dict(name="Internship Program", category="Training", price=150,
         duration_value=3, duration_unit="month", service_type="internship",
         short_description="A structured 3-month software engineering internship.",
         description="Hands-on mentorship across real projects with weekly reviews and a certificate.",
         features=["Mentor assigned", "Real project work", "Weekly reviews", "Certificate"],
         requirements=["CV", "Area of interest"],
         fields=[
             ("Full name", "full_name", "text", True, None),
             ("Education", "education", "text", True, None),
             ("Area of interest", "interest", "select", True,
              ["Mobile", "Web", "Backend", "UI/UX", "AI/ML", "Cybersecurity", "QA", "DevOps"]),
             ("Preferred duration", "duration", "select", False, ["1 month", "3 months", "6 months"]),
             ("Start date", "start_date", "date", False, None),
         ]),
    dict(name="Maintenance Plan", category="Maintenance", price=300,
         duration_value=6, duration_unit="month", service_type="subscription",
         short_description="6 months of updates, monitoring, and fixes.",
         description="Keep your software healthy with scheduled updates, security patches, and bug fixes.",
         features=["Security updates", "Bug fixing", "Performance monitoring", "Monthly report"],
         fields=[("System / app name", "system", "text", True, None),
                 ("Repository or hosting access", "access", "textarea", False, None)]),
    dict(name="Technical Support", category="Support", price=60,
         duration_value=30, duration_unit="day", service_type="subscription",
         short_description="30 days of priority technical support.",
         description="Direct access to an engineer for troubleshooting and guidance for 30 days.",
         features=["Priority queue", "Email & WhatsApp", "Screen-share sessions"],
         fields=[("What do you need help with?", "topic", "textarea", True, None)]),
    dict(name="UI/UX Design", category="Design", price=400,
         duration_value=14, duration_unit="day", service_type="system_development",
         short_description="Product design: flows, wireframes, and a polished UI kit.",
         description="Research-informed UX and a consistent, accessible UI system for your product.",
         features=["User flows", "Wireframes", "High-fidelity UI", "Design system", "Prototype"],
         fields=[("Product overview", "overview", "textarea", True, None),
                 ("Screens in scope", "screens", "textarea", True, None)]),
]


def seed_services(db):
    if db.query(Service).filter(Service.slug.isnot(None)).count() >= len(SERVICE_SEED):
        return
    for i, s in enumerate(SERVICE_SEED):
        slug = slugify(s["name"])
        if db.query(Service).filter(Service.slug == slug).first():
            continue
        svc = Service(
            name=s["name"], slug=slug, description=s["description"],
            short_description=s["short_description"], price=s["price"], currency="USD",
            category=s["category"], service_type=s["service_type"],
            duration_value=s["duration_value"], duration_unit=s["duration_unit"],
            features=s.get("features"), requirements=s.get("requirements"),
            process_steps=s.get("process_steps"), delivery_method=s.get("delivery_method"),
            status="published", availability="available",
            is_featured=(i < 3), popular=(i == 1), sort_order=i,
        )
        db.add(svc)
        db.flush()
        for j, (label, key, ftype, required, options) in enumerate(s.get("fields", [])):
            db.add(ServiceField(service_id=svc.id, label=label, field_key=key, field_type=ftype,
                                required=required, options=options, sort_order=j))
    db.commit()
    print("  + services seeded")


PRODUCT_SEED = [
    dict(name="Akagera POS", category="Business", version="2.4.0", platforms=["android", "windows", "cloud"],
         short_description="Point of sale, inventory, and reporting for retail.",
         description="A complete retail operations platform: sales, stock, suppliers, and daily reports.",
         features=["Offline mode", "Barcode scanning", "Multi-branch", "Daily Z-reports"],
         pricing_model="subscription", price=15, requires_license=True, is_featured=True,
         downloads=[("android", "Android APK", "2.4.0", "arm64", "18 MB", "Android 8+"),
                    ("windows", "Windows Installer", "2.4.0", "x64", "62 MB", "Windows 10+")]),
    dict(name="Akagera Books", category="Finance", version="1.9.2", platforms=["web", "windows", "macos"],
         short_description="Simple accounting for small businesses.",
         description="Invoicing, expenses, and tax-ready reports without the complexity.",
         features=["Invoicing", "Expense tracking", "VAT reports", "Multi-currency"],
         pricing_model="subscription", price=12, requires_license=True, is_featured=True,
         downloads=[("windows", "Windows Installer", "1.9.2", "x64", "48 MB", "Windows 10+"),
                    ("macos", "macOS Disk Image", "1.9.2", "universal", "44 MB", "macOS 12+")]),
    dict(name="Akagera Learn", category="Education", version="3.1.0", platforms=["android", "ios", "web"],
         short_description="School management and e-learning platform.",
         description="Students, classes, attendance, grades, and parent communication in one place.",
         features=["Attendance", "Gradebook", "Parent portal", "Timetable"],
         pricing_model="subscription", price=0, requires_license=False, is_featured=True,
         downloads=[("android", "Android APK", "3.1.0", "arm64", "22 MB", "Android 9+")]),
    dict(name="Akagera Connect", category="Communication", version="1.2.0", platforms=["android", "ios"],
         short_description="Team messaging for field operations.",
         description="Lightweight, low-data messaging and task updates for distributed teams.",
         features=["Low-data mode", "Broadcast lists", "Task updates", "Read receipts"],
         pricing_model="free", price=0, requires_license=False,
         downloads=[("android", "Android APK", "1.2.0", "universal", "12 MB", "Android 8+")]),
    dict(name="Akagera Guard", category="Security", version="0.9.5", platforms=["windows", "macos"],
         short_description="Endpoint monitoring for small offices.",
         description="Basic device inventory, update checks, and alerting for small IT setups.",
         features=["Device inventory", "Update checks", "Email alerts"],
         pricing_model="paid", price=39, requires_license=True,
         downloads=[("windows", "Windows Installer", "0.9.5", "x64", "30 MB", "Windows 10+")]),
    dict(name="Akagera DevKit", category="Developer Tools", version="0.4.1", platforms=["web", "cloud"],
         short_description="API scaffolding and deployment helpers.",
         description="CLI + templates to spin up production-ready FastAPI + React projects.",
         features=["Project templates", "Auth scaffolding", "Deploy scripts"],
         pricing_model="free", price=0, requires_license=False,
         website_url="https://github.com/akagerainc-boop"),
]


def seed_products(db):
    if db.query(App).filter(App.slug.isnot(None)).count() >= len(PRODUCT_SEED):
        return
    for i, p in enumerate(PRODUCT_SEED):
        slug = slugify(p["name"])
        app = db.query(App).filter(App.slug == slug).first()
        if not app:
            app = db.query(App).filter(App.name == p["name"]).first()
        if not app:
            app = App(name=p["name"])
            db.add(app)
        app.slug = slug
        app.category = p["category"]
        app.status = "published"
        app.version = p["version"]
        app.release_date = date.today() - timedelta(days=30 * (i + 1))
        app.platforms = p["platforms"]
        app.short_description = p["short_description"]
        app.description = p["description"]
        app.features = p["features"]
        app.pricing_model = p["pricing_model"]
        app.price = p["price"]
        app.requires_license = p["requires_license"]
        app.is_featured = p.get("is_featured", False)
        app.website_url = p.get("website_url")
        app.sort_order = i
        db.flush()
        if not app.downloads:
            for (plat, label, ver, arch, size, minos) in p.get("downloads", []):
                db.add(Download(product_id=app.id, platform=plat, label=label, version=ver,
                                architecture=arch, file_size=size, min_os=minos,
                                external_url="https://example.com/download",
                                release_notes="Initial seeded release.", released_at=date.today()))
    db.commit()
    print("  + products seeded")


def seed_misc(db):
    if db.query(Faq).count() == 0:
        faqs = [
            ("general", "How do I start a project?", "Pick a service, complete checkout, fill the project form, and we contact you within one business day."),
            ("general", "What payment methods do you accept?", "PayPal (cards) and Mobile Money. More providers can be added later."),
            ("billing", "Is there a refund policy?", "Yes — 14 days if work has not started. See the Refund Policy page."),
            ("licensing", "How do license keys work?", "After payment you receive a key in your dashboard that activates the product for its license period."),
            ("support", "How do I get support?", "Open a ticket in the Support Center or message us on WhatsApp."),
        ]
        for i, (cat, q, a) in enumerate(faqs):
            db.add(Faq(category=cat, question=q, answer=a, sort_order=i))
    if db.query(Testimonial).count() == 0:
        t = [
            ("Jean-Paul K.", "Operations Lead", "Kigali Retail Group", "Akagera POS replaced three spreadsheets. Daily reconciliation now takes minutes.", 5),
            ("Aline U.", "Head Teacher", "Green Hills School", "Akagera Learn made attendance and parent updates effortless.", 5),
            ("David M.", "Founder", "PayFlow", "They shipped our MVP in six weeks and the code was clean.", 5),
        ]
        for i, (n, r, c, q, rt) in enumerate(t):
            db.add(Testimonial(name=n, role=r, company=c, quote=q, rating=rt, sort_order=i))
    if db.query(Industry).count() == 0:
        for i, ind in enumerate(sd.INDUSTRIES):
            db.add(Industry(slug=ind["slug"], name=ind["name"], icon=ind["icon"],
                            summary=ind["summary"],
                            body=f"Akagera Inc builds software for the {ind['name'].lower()} sector: "
                                 f"{ind['summary']} We handle discovery, delivery, and maintenance.",
                            sort_order=i))
    if db.query(BlogPost).count() == 0:
        posts = [
            ("Choosing between native and cross-platform in 2026", "mobile-development",
             "A practical decision guide for teams shipping their first mobile app."),
            ("How we keep image-heavy pages fast", "web-development",
             "Caching, lazy-loading, and blur-up placeholders — the techniques behind Akagera's fast media."),
        ]
        for i, (title, cat, excerpt) in enumerate(posts):
            db.add(BlogPost(slug=slugify(title), title=title, excerpt=excerpt, category=cat,
                            author="Akagera Inc", status="published", reading_time=5,
                            is_featured=(i == 0), published_at=datetime.utcnow() - timedelta(days=i * 7),
                            body=f"<p>{excerpt}</p><p>Full article content is managed from the admin dashboard.</p>"))
    if db.query(Internship).count() == 0:
        db.add(Internship(slug="software-engineering-internship", title="Software Engineering Internship",
                          department="Engineering",
                          description="Work alongside senior engineers on live Akagera products.",
                          requirements=["Basic programming (any language)", "Git", "Willingness to learn"],
                          duration_label="3 months", positions=4, is_free=False, price=150,
                          deadline=date.today() + timedelta(days=45), status="open"))
    if db.query(JobPosition).count() == 0:
        db.add(JobPosition(slug="senior-backend-engineer", title="Senior Backend Engineer",
                           department="Engineering", location="Musanze / Remote",
                           employment_type="Full-time",
                           description="Own backend services across Akagera's product portfolio.",
                           responsibilities=["Design APIs", "Own data models", "Mentor juniors"],
                           requirements=["4+ years backend", "Python or Node", "SQL"],
                           benefits=["Competitive salary", "Remote-friendly", "Learning budget"],
                           status="open"))
    if db.query(CaseStudy).count() == 0:
        db.add(CaseStudy(slug="kigali-retail-pos-rollout", title="Rolling out POS to 12 retail branches",
                         client="Kigali Retail Group", category="Retail",
                         summary="A 6-week rollout of Akagera POS across 12 branches with offline support.",
                         challenge="Unreliable connectivity and inconsistent stock data across branches.",
                         solution="Offline-first POS with nightly sync and a central reporting dashboard.",
                         results="Daily reconciliation time cut by 80%; stock accuracy above 98%.",
                         technologies=["React", "FastAPI", "MySQL"], platforms=["android", "windows"],
                         is_featured=True, status="published"))
    if db.query(DocPage).count() == 0:
        docs = [
            ("getting-started", "Getting Started", "Getting Started with Akagera",
             "Create an account, choose a product or service, and complete checkout."),
            ("installation", "Products", "Installing Akagera apps",
             "Download the installer for your platform from the Downloads page and follow the prompts."),
            ("licensing", "Products", "Activating a license",
             "Copy your license key from the dashboard and paste it into the app's activation screen."),
            ("api-overview", "Developers", "API overview",
             "The Akagera API is REST over HTTPS. Public endpoints are under /api/."),
        ]
        for i, (slug, section, title, body) in enumerate(docs):
            db.add(DocPage(slug=slug, section=section, title=title, body=f"<p>{body}</p>", sort_order=i))
    db.commit()
    print("  + misc content seeded")


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding Akagera Inc database…")
        seed_site_content(db)
        seed_admin(db)
        seed_navigation(db)
        seed_categories(db)
        seed_services(db)
        seed_products(db)
        seed_misc(db)
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
