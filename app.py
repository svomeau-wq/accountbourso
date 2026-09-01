"""
Application bancaire inspirée de Boursorama
-------------------------------------------
Lance avec :
    pip install -r requirements.txt
    python app.py
Puis va sur http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from datetime import datetime, timedelta
from io import BytesIO
import random
import os
import base64
import logging
import resend
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "change-me-in-production"

# Configuration Resend
resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL  = os.environ.get("SENDER_EMAIL", "noreply@crasdor.org")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Données factices (en mémoire) - À remplacer par une vraie base de données
# -----------------------------------------------------------------------------

USERS = {
    "990303": {
        "password": "0275",
        "nom": "Linas Jean Michel",
        "email": "jeanfnnc@gmail.com",
        "adresse": "5 rue Lamartine ,17000 Larochelle",
        "iban": "FR76 1234 5678 9012 3456 7890 123",
        "bic": "BOUSFRPPXXX",
        "compte_courant": 4000000.000,
        "livret": 1000000.00,
        "pea": 8420.50,
    }
}

OPERATIONS = [
    # Mai 2026
    {"date": "15/06/2026", "libelle": "Virements Sce",        "type": "Carte",     "montant": 560.040},
    {"date": "04/06/2026", "libelle": "VIREMENT  ACME",  "type": "Virement",  "montant": 60250.00},
    {"date": "13/01/2026", "libelle": "NETFLIX",                "type": "Prélèvement","montant": -13.49},
    {"date": "12/01/2026", "libelle": "SNCF CONNECT",           "type": "Carte",     "montant": -89.00},
    {"date": "11/01/2026", "libelle": "EDF ENERGIE",            "type": "Prélèvement","montant": -78.20},
    {"date": "10/01/2026", "libelle": "RETRAIT DAB BNP",        "type": "Retrait",   "montant": -100.00},
    {"date": "09/01/2026", "libelle": "AMAZON FR",              "type": "Carte",     "montant": -34.99},
    {"date": "08/01/2026", "libelle": "BOULANGERIE LE PETIT",   "type": "Carte",     "montant": -8.50},
    {"date": "07/01/2026", "libelle": "FREE MOBILE",            "type": "Prélèvement","montant": -19.99},
    {"date": "05/01/2026", "libelle": "VIREMENT VERS LIVRET",   "type": "Virement",  "montant": -500.00},
    {"date": "04/01/2026", "libelle": "UBER EATS",              "type": "Carte",     "montant": -24.30},
    {"date": "03/01/2026", "libelle": "FNAC PARIS",             "type": "Carte",     "montant": -149.90},
    # Avril 2026
    {"date": "30/12/2025", "libelle": "VIREMENT SALAIRE ACME",  "type": "Virement",  "montant": 2850.00},
    {"date": "28/12/2025", "libelle": "DECATHLON",              "type": "Carte",     "montant": -84.50},
    {"date": "26/12/2025", "libelle": "RESTAURANT LE BISTROT",  "type": "Carte",     "montant": -67.80},
    {"date": "24/12/2025", "libelle": "VIRT M. DUPONT",         "type": "Virement",  "montant": -200.00},
    {"date": "20/12/2025", "libelle": "GALERIES LAFAYETTE",     "type": "Carte",     "montant": -245.00},
    {"date": "18/12/2025", "libelle": "EDF ENERGIE",            "type": "Prélèvement","montant": -78.20},
    {"date": "15/12/2025", "libelle": "SPOTIFY",                "type": "Prélèvement","montant": -9.99},
    {"date": "10/12/2025", "libelle": "NETFLIX",                "type": "Prélèvement","montant": -13.49},
    # Mars 2026
    {"date": "30/11/2025", "libelle": "VIREMENT SALAIRE ACME",  "type": "Virement",  "montant": 2850.00},
    {"date": "25/11/2025", "libelle": "LECLERC DRIVE",          "type": "Carte",     "montant": -156.40},
    {"date": "22/11/2025", "libelle": "MAAF ASSURANCE",         "type": "Prélèvement","montant": -56.30},
    {"date": "20/11/2025", "libelle": "AMAZON FR",              "type": "Carte",     "montant": -78.90},
    {"date": "15/11/2025", "libelle": "RETRAIT DAB",            "type": "Retrait",   "montant": -150.00},
]

DOMICILIATIONS = [
    {"creancier": "EDF",         "reference": "REF-EDF-882371",  "type": "Énergie",       "montant_estime": 78.20,  "prochaine": "11/02/2026", "statut": "Actif"},
    {"creancier": "FREE MOBILE", "reference": "REF-FREE-44521",  "type": "Télécom",       "montant_estime": 19.99,  "prochaine": "07/02/2026", "statut": "Actif"},
    {"creancier": "NETFLIX",     "reference": "REF-NFLX-99812",  "type": "Abonnement",    "montant_estime": 13.49,  "prochaine": "13/02/2026", "statut": "Actif"},
    {"creancier": "VEOLIA EAU",  "reference": "REF-VEO-21183",   "type": "Eau",           "montant_estime": 42.00,  "prochaine": "20/02/2026", "statut": "Actif"},
    {"creancier": "ASSURANCE MAAF","reference": "REF-MAAF-77621","type": "Assurance",     "montant_estime": 56.30,  "prochaine": "01/02/2026", "statut": "Actif"},
    {"creancier": "SPOTIFY",     "reference": "REF-SPOT-10245",  "type": "Abonnement",    "montant_estime": 9.99,   "prochaine": "18/02/2026", "statut": "Suspendu"},
]

CARTES = [
    {
        "type": "Visa Premier",
        "numero": "4974 •••• •••• 8821",
        "expiration": "08/28",
        "titulaire": "Linas Jean Michel",
        "statut": "Active",
        "plafond_paiement": 5000,
        "plafond_retrait": 1000,
        "utilise_paiement": 1247.60,
        "utilise_retrait": 250.00,
        "couleur": "#1A1A2E",
    },
    {
        "type": "Mastercard Welcome",
        "numero": "5283 •••• •••• 4412",
        "expiration": "03/27",
        "titulaire": "Linas Jean Michel",
        "statut": "Active",
        "plafond_paiement": 2000,
        "plafond_retrait": 500,
        "utilise_paiement": 348.20,
        "utilise_retrait": 0.00,
        "couleur": "#E6007E",
    },
]

PORTEFEUILLE_PEA = [
    {"titre": "LVMH",         "isin": "FR0000121014", "quantite": 8,  "cours": 720.50, "variation": 2.4},
    {"titre": "TotalEnergies","isin": "FR0000120271", "quantite": 25, "cours": 58.20,  "variation": -0.8},
    {"titre": "Air Liquide",  "isin": "FR0000120073", "quantite": 12, "cours": 175.40, "variation": 1.2},
    {"titre": "Sanofi",       "isin": "FR0000120578", "quantite": 18, "cours": 94.80,  "variation": 0.5},
    {"titre": "BNP Paribas",  "isin": "FR0000131104", "quantite": 30, "cours": 62.10,  "variation": -1.5},
]

NOTIFICATIONS = [
    {"date": "15/01/2026", "type": "info",    "titre": "Virement reçu",         "message": "Vous avez reçu un virement de 2 850,00 € de ACME SAS.", "lu": False},
    {"date": "14/01/2026", "type": "warning", "titre": "Plafond carte à 75%",   "message": "Votre carte Visa Premier a atteint 75% du plafond mensuel.", "lu": False},
    {"date": "12/01/2026", "type": "info",    "titre": "Nouveau relevé",        "message": "Votre relevé de décembre 2025 est disponible au téléchargement.", "lu": True},
    {"date": "10/01/2026", "type": "success", "titre": "Économie réalisée",     "message": "Bravo ! Vous avez économisé 12% par rapport au mois dernier.", "lu": True},
    {"date": "05/01/2026", "type": "warning", "titre": "Prélèvement à venir",   "message": "Prélèvement EDF de 78,20 € prévu le 11/02/2026.", "lu": True},
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user" in session:
        return USERS.get(session["user"])
    return None


# -----------------------------------------------------------------------------
# Routes principales
# -----------------------------------------------------------------------------

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        password = request.form.get("password", "").strip()
        user = USERS.get(identifiant)
        if user and user["password"] == password:
            session["user"] = identifiant
            return redirect(url_for("dashboard"))
        flash("Identifiant ou mot de passe incorrect.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    total = user["compte_courant"] + user["livret"] + user["pea"]
    notif_non_lues = sum(1 for n in NOTIFICATIONS if not n["lu"])
    return render_template(
        "dashboard.html",
        user=user,
        operations=OPERATIONS[:5],
        total=total,
        notif_non_lues=notif_non_lues,
    )


@app.route("/releve")
@login_required
def releve():
    user = current_user()
    # Filtres
    q       = request.args.get("q", "").strip().lower()
    op_type = request.args.get("type", "").strip()
    mois    = request.args.get("mois", "").strip()

    ops_filtrees = OPERATIONS
    if q:
        ops_filtrees = [o for o in ops_filtrees if q in o["libelle"].lower()]
    if op_type:
        ops_filtrees = [o for o in ops_filtrees if o["type"] == op_type]
    if mois:
        ops_filtrees = [o for o in ops_filtrees if o["date"].endswith(mois)]

    credits = sum(op["montant"] for op in ops_filtrees if op["montant"] > 0)
    debits  = sum(op["montant"] for op in ops_filtrees if op["montant"] < 0)

    # Liste des mois disponibles
    mois_dispo = sorted({o["date"][3:] for o in OPERATIONS}, reverse=True)

    return render_template(
        "releve.html",
        user=user,
        operations=ops_filtrees,
        credits=credits,
        debits=debits,
        solde=user["compte_courant"],
        q=q,
        op_type=op_type,
        mois=mois,
        mois_dispo=mois_dispo,
    )


@app.route("/domiciliation")
@login_required
def domiciliation():
    user = current_user()
    total_mensuel = sum(d["montant_estime"] for d in DOMICILIATIONS if d["statut"] == "Actif")
    return render_template(
        "domiciliation.html",
        user=user,
        domiciliations=DOMICILIATIONS,
        total_mensuel=total_mensuel,
    )


@app.route("/virement", methods=["GET", "POST"])
@login_required
def virement():
    user = current_user()
    if request.method == "POST":
        prenom   = request.form.get("prenom", "").strip()
        nom      = request.form.get("nom", "").strip()
        adresse  = request.form.get("adresse", "").strip()
        ville    = request.form.get("ville", "").strip()
        pays     = request.form.get("pays", "").strip()
        email    = request.form.get("email", "").strip()
        montant  = request.form.get("montant", "").strip()
        motif    = request.form.get("motif", "").strip()

        try:
            montant_f = float(montant)
            if montant_f <= 0:
                raise ValueError
            if montant_f > user["compte_courant"]:
                flash("Solde insuffisant pour effectuer ce virement.", "error")
            else:
                # Référence unique du virement
                reference = "VIR-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + str(random.randint(1000, 9999))
                date_op   = datetime.now().strftime("%d/%m/%Y à %H:%M")

                # Débit du compte
                user["compte_courant"] -= montant_f
                OPERATIONS.insert(0, {
                    "date": datetime.now().strftime("%d/%m/%Y"),
                    "libelle": f"VIREMENT {prenom.upper()} {nom.upper()}",
                    "type": "Virement",
                    "montant": -montant_f,
                })

                # Génère le PDF de confirmation
                pdf_bytes = generate_virement_pdf(
                    reference=reference,
                    date_op=date_op,
                    emetteur=user,
                    prenom=prenom, nom=nom, adresse=adresse, ville=ville, pays=pays,
                    email=email, montant=montant_f, motif=motif,
                )

                # Envoie l'email avec PDF en pièce jointe
                email_ok, email_err = send_virement_email(
                    to_email=email, prenom=prenom, nom=nom,
                    montant=montant_f, motif=motif, reference=reference,
                    emetteur_nom=user["nom"], pdf_bytes=pdf_bytes,
                )

                if email_ok:
                    flash(f"✓ Virement de {montant_f:.2f} € validé. Confirmation envoyée à {email}.", "success")
                else:
                    flash(f"Virement effectué mais l'email n'a pas pu être envoyé : {email_err}", "error")
                return redirect(url_for("dashboard"))
        except ValueError:
            flash("Montant invalide.", "error")
    return render_template("virement.html", user=user)


# -----------------------------------------------------------------------------
# Génération du PDF de confirmation de virement
# -----------------------------------------------------------------------------

def generate_virement_pdf(reference, date_op, emetteur, prenom, nom, adresse, ville,
                          pays, email, montant, motif):
    """Génère un PDF de confirmation de virement et renvoie les bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Bandeau rose
    c.setFillColor(HexColor("#E6007E"))
    c.rect(0, height - 3.5*cm, width, 3.5*cm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 26)
    c.drawString(2*cm, height - 2*cm, "BoursoBank")
    c.setFont("Helvetica", 13)
    c.drawString(2*cm, height - 2.8*cm, "Confirmation de virement bancaire")

    # Référence + date en haut à droite
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 2*cm, height - 2*cm, f"Référence : {reference}")
    c.drawRightString(width - 2*cm, height - 2.5*cm, f"Émis le {date_op}")

    # ----- Bloc émetteur -----
    y = height - 5*cm
    c.setFillColor(HexColor("#1A1A2E"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "ÉMETTEUR")
    c.setStrokeColor(HexColor("#E6007E"))
    c.setLineWidth(2)
    c.line(2*cm, y - 0.15*cm, 5*cm, y - 0.15*cm)
    y -= 0.8*cm
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, y, emetteur["nom"]);                          y -= 0.5*cm
    c.drawString(2*cm, y, emetteur["adresse"]);                      y -= 0.5*cm
    c.drawString(2*cm, y, f"IBAN : {emetteur['iban']}");             y -= 0.5*cm
    c.drawString(2*cm, y, f"BIC  : {emetteur['bic']}")

    # ----- Bloc bénéficiaire -----
    y -= 1.2*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "BÉNÉFICIAIRE")
    c.line(2*cm, y - 0.15*cm, 6.2*cm, y - 0.15*cm)
    y -= 0.8*cm
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, y, f"{prenom} {nom}");                        y -= 0.5*cm
    c.drawString(2*cm, y, adresse);                                  y -= 0.5*cm
    c.drawString(2*cm, y, f"{ville}, {pays}");                       y -= 0.5*cm
    c.drawString(2*cm, y, f"Email : {email}")

    # ----- Bloc opération (encadré) -----
    y -= 1.5*cm
    c.setFillColor(HexColor("#fef5fb"))
    c.rect(2*cm, y - 4.5*cm, width - 4*cm, 4.5*cm, fill=1, stroke=0)
    c.setStrokeColor(HexColor("#E6007E"))
    c.setLineWidth(1)
    c.rect(2*cm, y - 4.5*cm, width - 4*cm, 4.5*cm, fill=0, stroke=1)

    c.setFillColor(HexColor("#1A1A2E"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(2.5*cm, y - 0.8*cm, "DÉTAILS DE L'OPÉRATION")

    c.setFont("Helvetica", 10)
    c.drawString(2.5*cm, y - 1.6*cm, "Montant :")
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(HexColor("#E6007E"))
    c.drawString(2.5*cm, y - 2.4*cm, f"{montant:,.2f} EUR".replace(",", " "))

    c.setFillColor(HexColor("#1A1A2E"))
    c.setFont("Helvetica", 10)
    c.drawString(2.5*cm, y - 3.2*cm, f"Motif : {motif}")
    c.drawString(2.5*cm, y - 3.8*cm, f"Référence : {reference}")
    c.drawString(2.5*cm, y - 4.3*cm, f"Date d'exécution : {date_op}")

    # ----- Statut -----
    c.setFillColor(HexColor("#00A86B"))
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 2.5*cm, y - 0.8*cm, "✓ VALIDÉ")

    # ----- Footer -----
    c.setFillColor(HexColor("#666666"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(2*cm, 2.5*cm, "Ce document est une confirmation officielle de virement émis par BoursoBank.")
    c.drawString(2*cm, 2.1*cm, "Conservez-le pour vos archives. En cas de litige, contactez votre conseiller.")
    c.drawString(2*cm, 1.5*cm, "BoursoBank © 2026 - Tous droits réservés")
    c.drawRightString(width - 2*cm, 1.5*cm, "Document généré automatiquement")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# Envoi de l'email Resend avec PDF en pièce jointe
# -----------------------------------------------------------------------------

def send_virement_email(to_email, prenom, nom, montant, motif, reference,
                        emetteur_nom, pdf_bytes):
    """Envoie l'email de confirmation via Resend avec le PDF en pièce jointe."""
    if not resend.api_key:
        return False, "Clé API Resend manquante"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; font-family:Helvetica,Arial,sans-serif; background:#f5f5f7;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f7; padding:30px 0;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.08);">
            <tr>
              <td style="background:linear-gradient(135deg,#E6007E 0%,#C20069 100%); padding:32px; text-align:center;">
                <h1 style="color:#fff; margin:0; font-size:28px; font-weight:800;">BoursoBank</h1>
                <p style="color:#fff; margin:8px 0 0; opacity:0.9; font-size:14px;">Confirmation de virement</p>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <h2 style="color:#1A1A2E; margin:0 0 16px; font-size:20px;">Bonjour {prenom} {nom},</h2>
                <p style="color:#444; font-size:15px; line-height:1.6;">
                  Vous avez reçu un virement de la part de <strong>{emetteur_nom}</strong>.
                  Vous trouverez le détail de l'opération ci-dessous, ainsi qu'une confirmation officielle en pièce jointe (PDF).
                </p>

                <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef5fb; border:1px solid #E6007E; border-radius:8px; margin:24px 0; padding:20px;">
                  <tr><td style="padding:8px 0; color:#666; font-size:13px;">Montant</td>
                      <td style="padding:8px 0; text-align:right; font-size:24px; font-weight:bold; color:#E6007E;">{montant:.2f} €</td></tr>
                  <tr><td style="padding:8px 0; color:#666; font-size:13px;">Motif</td>
                      <td style="padding:8px 0; text-align:right; color:#1A1A2E; font-weight:600;">{motif}</td></tr>
                  <tr><td style="padding:8px 0; color:#666; font-size:13px;">Référence</td>
                      <td style="padding:8px 0; text-align:right; color:#1A1A2E; font-family:monospace; font-size:13px;">{reference}</td></tr>
                  <tr><td style="padding:8px 0; color:#666; font-size:13px;">Statut</td>
                      <td style="padding:8px 0; text-align:right; color:#00A86B; font-weight:bold;">✓ Validé</td></tr>
                </table>

                <p style="color:#444; font-size:14px; line-height:1.6;">
                  📎 <strong>Pièce jointe :</strong> Confirmation officielle au format PDF.
                </p>

                <p style="color:#999; font-size:12px; line-height:1.6; margin-top:32px; padding-top:20px; border-top:1px solid #eee;">
                  Cet email est généré automatiquement, merci de ne pas y répondre.<br>
                  Pour toute question, contactez votre conseiller BoursoBank.
                </p>
              </td>
            </tr>
            <tr>
              <td style="background:#1A1A2E; color:#fff; padding:20px; text-align:center; font-size:12px;">
                BoursoBank © 2026 — Tous droits réservés
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    params = {
        "from": SENDER_EMAIL,
        "to": [to_email],
        "subject": f"Confirmation de virement - {montant:.2f} € reçus de {emetteur_nom}",
        "html": html_content,
        "attachments": [
            {
                "filename": f"confirmation_virement_{reference}.pdf",
                "content": pdf_b64,
            }
        ],
    }

    try:
        result = resend.Emails.send(params)
        logger.info(f"Email Resend envoyé à {to_email} (id={result.get('id')})")
        return True, None
    except Exception as e:
        logger.exception("Erreur Resend")
        return False, str(e)


@app.route("/coordonnees")
@login_required
def coordonnees():
    user = current_user()
    return render_template("coordonnees.html", user=user)


# -----------------------------------------------------------------------------
# Nouvelles routes : Cartes, Épargne, Crédit, Notifications, PDF
# -----------------------------------------------------------------------------

@app.route("/cartes")
@login_required
def cartes():
    user = current_user()
    return render_template("cartes.html", user=user, cartes=CARTES)


@app.route("/epargne")
@login_required
def epargne():
    user = current_user()
    # Valorisation du portefeuille PEA
    valorisation = sum(t["quantite"] * t["cours"] for t in PORTEFEUILLE_PEA)
    plus_value   = valorisation - 7500  # PRU fictif
    return render_template(
        "epargne.html",
        user=user,
        portefeuille=PORTEFEUILLE_PEA,
        valorisation=valorisation,
        plus_value=plus_value,
    )


@app.route("/credit", methods=["GET", "POST"])
@login_required
def credit():
    user = current_user()
    result = None
    if request.method == "POST":
        try:
            montant = float(request.form.get("montant", 0))
            duree   = int(request.form.get("duree", 0))    # en mois
            taux    = float(request.form.get("taux", 0))   # en %
            if montant > 0 and duree > 0 and taux >= 0:
                taux_mensuel = (taux / 100) / 12
                if taux_mensuel == 0:
                    mensualite = montant / duree
                else:
                    mensualite = montant * taux_mensuel / (1 - (1 + taux_mensuel) ** -duree)
                cout_total  = mensualite * duree
                cout_credit = cout_total - montant
                result = {
                    "mensualite": mensualite,
                    "cout_total": cout_total,
                    "cout_credit": cout_credit,
                    "montant": montant,
                    "duree": duree,
                    "taux": taux,
                }
        except ValueError:
            flash("Valeurs invalides.", "error")
    return render_template("credit.html", user=user, result=result)


@app.route("/notifications")
@login_required
def notifications():
    user = current_user()
    return render_template("notifications.html", user=user, notifications=NOTIFICATIONS)


@app.route("/rib.pdf")
@login_required
def rib_pdf():
    """Génère un PDF du RIB avec ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor

    user = current_user()
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Bandeau rose en haut
    c.setFillColor(HexColor("#E6007E"))
    c.rect(0, height - 3*cm, width, 3*cm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(2*cm, height - 2*cm, "BoursoBank")
    c.setFont("Helvetica", 12)
    c.drawString(2*cm, height - 2.6*cm, "Relevé d'Identité Bancaire (RIB)")

    # Date
    c.setFillColor(HexColor("#1A1A2E"))
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 2*cm, height - 2*cm, datetime.now().strftime("Émis le %d/%m/%Y"))

    # Bloc Titulaire
    y = height - 5*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "TITULAIRE DU COMPTE")
    c.setFont("Helvetica", 11)
    y -= 0.7*cm
    c.drawString(2*cm, y, user["nom"])
    y -= 0.5*cm
    c.drawString(2*cm, y, user["adresse"])
    y -= 0.5*cm
    c.drawString(2*cm, y, user["email"])

    # Bloc Identité bancaire
    y -= 1.2*cm
    c.setStrokeColor(HexColor("#E6007E"))
    c.setLineWidth(2)
    c.line(2*cm, y, width - 2*cm, y)
    y -= 0.8*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "IDENTITÉ BANCAIRE")

    y -= 1*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y, "IBAN")
    c.setFont("Helvetica", 11)
    c.drawString(5*cm, y, user["iban"])

    y -= 0.7*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y, "BIC")
    c.setFont("Helvetica", 11)
    c.drawString(5*cm, y, user["bic"])

    y -= 0.7*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y, "Banque")
    c.setFont("Helvetica", 11)
    c.drawString(5*cm, y, "BoursoBank")

    y -= 0.7*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y, "Domiciliation")
    c.setFont("Helvetica", 11)
    c.drawString(5*cm, y, "BoursoBank Paris")

    # Note bas de page
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(HexColor("#666666"))
    c.drawString(2*cm, 2*cm, "Communiquez ce RIB à vos créanciers pour mettre en place un prélèvement SEPA.")
    c.drawString(2*cm, 1.6*cm, "Ce document est émis à titre informatif - BoursoBank © 2026")

    c.showPage()
    c.save()
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"RIB_{user['nom'].replace(' ', '_')}.pdf",
        mimetype="application/pdf",
    )


# -----------------------------------------------------------------------------
# Lancement
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
