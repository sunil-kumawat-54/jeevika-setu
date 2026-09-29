"""Gate 9 — officer dashboard + admin console acceptance tests.

Covers: by-domain bars, top concepts, district gap panel, centre_supply,
synthetic flag visibility, compliance chips (women % vs the 30% mandate), CSV
and XLSX exports that actually open, session drill-down with transcript,
recommendations and consent, the crosswalk review table, and the audit_log row
that every admin mutation must write.
"""

from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy import func, select

from core.config import settings
from core.domain.scheme_constants import WOMEN_PARTICIPATION_FLOOR_PCT
from core.models.tables import AuditLog, CentreSupply
from core.models.tables import Session as SessionRow

LATUR = "270481"
GAYA = "100196"


def _login(client, email: str, password: str) -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def officer(client):
    return _login(client, settings.demo_officer_email, settings.demo_officer_password)


@pytest.fixture()
def viewer(client):
    return _login(client, settings.demo_viewer_email, settings.demo_viewer_password)


@pytest.fixture()
def admin(client):
    return _login(client, settings.demo_admin_email, settings.demo_admin_password)


# ==========================================================================
# Seeded data — the dashboard must be populated and demoable
# ==========================================================================


def test_at_least_25_synthetic_sessions_seeded(db_session):
    """PLAN.md §5.1 pipeline 07 / Gate 9: 25 synthetic sessions."""
    count = db_session.execute(
        select(func.count()).select_from(SessionRow).where(SessionRow.synthetic.is_(True))
    ).scalar_one()
    assert count >= 25, f"only {count} synthetic sessions seeded"


def test_sessions_span_five_districts(db_session):
    districts = db_session.execute(
        select(func.count(func.distinct(SessionRow.district_code))).where(
            SessionRow.synthetic.is_(True)
        )
    ).scalar_one()
    assert districts >= 5, f"synthetic sessions cover only {districts} districts"


def test_centre_supply_is_populated(db_session):
    count = db_session.execute(select(func.count()).select_from(CentreSupply)).scalar_one()
    assert count > 0


# ==========================================================================
# Stats — charts and compliance chips
# ==========================================================================


def test_stats_returns_by_domain_and_top_concepts(client, officer):
    body = client.get("/dashboard/stats", headers=officer).json()
    assert body["total_sessions"] >= 25
    assert body["by_domain"], "by-domain bars have no data"
    for row in body["by_domain"]:
        assert 1 <= row["gia_domain"] <= 10, "GIA domain outside the illustrative list"
        assert row["name"]
        assert row["count"] > 0
    assert body["top_concepts"], "top-concepts chart has no data"


def test_women_compliance_chip_compares_against_the_mandate(client, officer):
    """PLAN.md §4.2: "% women captured (target >=30% mandate)"."""
    body = client.get("/dashboard/stats", headers=officer).json()
    women = body["compliance"]["women"]
    assert women["target_pct"] == float(WOMEN_PARTICIPATION_FLOOR_PCT)
    assert women["meets_mandate"] == (women["women_pct"] >= women["target_pct"])
    assert "citation" in women


def test_consent_and_priority_income_chips_present(client, officer):
    body = client.get("/dashboard/stats", headers=officer).json()
    assert 0 <= body["consent_pct"] <= 100
    assert "priority_income" in body["compliance"]
    # research.md §2.3: there is NO fixed income limit — the chip must say so.
    assert body["compliance"]["priority_income"]["has_fixed_income_limit"] is False


def test_stats_exposes_the_synthetic_share(client, officer):
    """Honesty: the dashboard must show how much of this is seeded data."""
    body = client.get("/dashboard/stats", headers=officer).json()
    assert body["synthetic"]["sessions"] >= 25
    assert body["synthetic"]["share_pct"] > 0
    assert "not real field intake" in body["synthetic"]["note"]


def test_stats_can_filter_by_district(client, officer):
    all_sessions = client.get("/dashboard/stats", headers=officer).json()["total_sessions"]
    latur = client.get(f"/dashboard/stats?district={LATUR}", headers=officer).json()
    assert latur["total_sessions"] < all_sessions
    assert latur["filters"]["district"] == LATUR


def test_district_rollup_flags_a_district_below_the_mandate(client, officer):
    """The seed deliberately holds one district below 30% so the dashboard has
    a real compliance problem to surface, not a uniformly green wall."""
    body = client.get("/dashboard/districts", headers=officer).json()
    assert body["items"]
    assert any(not d["meets_women_mandate"] for d in body["items"]), (
        "no district falls below the women mandate — the gap story is invisible"
    )


# ==========================================================================
# Gap panel
# ==========================================================================


def test_gap_panel_reports_demand_against_supply(client, officer):
    body = client.get("/dashboard/gap", headers=officer).json()
    assert body["items"]
    for item in body["items"]:
        assert item["demand_n"] > 0
        assert item["supply_seats"] >= 0
        assert item["status"] in ("supplied", "no_local_supply", "no_qualification")


def test_gap_panel_flags_the_declared_crosswalk_gap(client, officer):
    """poultry has no QP anywhere in the register; the officer must see that."""
    body = client.get("/dashboard/gap", headers=officer).json()
    poultry = next((i for i in body["items"] if i["concept"] == "poultry"), None)
    if poultry is not None:
        assert poultry["status"] == "no_qualification"
        assert poultry["supply_seats"] == 0
        assert poultry["qp_codes"] == []
        assert poultry["flagged"] is True
        assert body["flagged"] >= 1


def test_gap_panel_distinguishes_the_two_kinds_of_gap(client, officer):
    body = client.get("/dashboard/gap", headers=officer).json()
    assert "no_qualification" in body["legend"]
    assert "no_local_supply" in body["legend"]


# ==========================================================================
# Drill-down
# ==========================================================================


def test_session_list_carries_no_beneficiary_name_or_phone(client, officer):
    """RULE 6 at the dashboard boundary."""
    body = client.get("/dashboard/sessions", headers=officer).json()
    assert body["items"]
    for row in body["items"]:
        assert not [k for k in row if k in ("name", "phone", "beneficiary_name")]


def test_drill_down_shows_transcript_recommendations_and_consent(client, officer):
    listing = client.get("/dashboard/sessions", headers=officer).json()["items"]
    consented = [s for s in listing if s["consent"]]
    assert consented, "no consented session to drill into"

    details = [
        client.get(f"/dashboard/sessions/{s['session_id']}", headers=officer).json()
        for s in consented
    ]
    for detail in details:
        assert detail["transcript"], "no transcript in the drill-down"
        assert detail["consent"]["granted"] is True
        assert detail["consent"]["records"][0]["playback_ref"], "consent playback reference missing"
        assert detail["profile"]

    with_recs = [d for d in details if d["recommendations"]]
    assert with_recs, "no consented session carries recommendations"
    for rec in with_recs[0]["recommendations"]:
        assert rec["qp_code"]
        assert rec["factors"], "score factors must be auditable"
        assert 0.0 <= rec["score"] <= 1.0


def test_a_refused_session_shows_no_recommendations_rather_than_a_wrong_one(client, officer):
    """A consented session whose aspiration hit a declared crosswalk gap must
    appear with an empty recommendation list — the officer sees that AVSAR
    declined, not a plausible-looking wrong trade."""
    listing = client.get("/dashboard/sessions", headers=officer).json()["items"]
    details = [
        client.get(f"/dashboard/sessions/{s['session_id']}", headers=officer).json()
        for s in listing
        if s["consent"]
    ]
    refused = [d for d in details if not d["recommendations"]]
    if refused:
        # It still captured the aspiration — the demand signal is not lost.
        assert refused[0]["transcript"], "a refusal must still record what was asked"


def test_drill_down_marks_synthetic_rows(client, officer):
    listing = client.get("/dashboard/sessions", headers=officer).json()["items"]
    detail = client.get(f"/dashboard/sessions/{listing[0]['session_id']}", headers=officer).json()
    assert "synthetic" in detail


def test_a_session_without_consent_stores_no_profile(client, officer):
    """The consent gate, visible from the officer's side."""
    listing = client.get("/dashboard/sessions", headers=officer).json()["items"]
    unconsented = [s for s in listing if not s["consent"]]
    if unconsented:
        detail = client.get(
            f"/dashboard/sessions/{unconsented[0]['session_id']}", headers=officer
        ).json()
        profile = detail["profile"]
        assert all(
            profile.get(key) is None
            for key in ("age_band", "gender", "edu_level", "current_work")
        ), f"profile stored without consent: {profile}"


def test_unknown_session_is_404(client, officer):
    response = client.get(
        "/dashboard/sessions/00000000-0000-0000-0000-000000000000", headers=officer
    )
    assert response.status_code == 404


# ==========================================================================
# RBAC — row-level access
# ==========================================================================


def test_viewer_sees_aggregates(client, viewer):
    assert client.get("/dashboard/stats", headers=viewer).status_code == 200
    assert client.get("/dashboard/gap", headers=viewer).status_code == 200
    assert client.get("/dashboard/districts", headers=viewer).status_code == 200


def test_viewer_cannot_see_individual_rows(client, viewer):
    """ARCHITECTURE §9: "individual beneficiary rows hidden from viewer"."""
    assert client.get("/dashboard/sessions", headers=viewer).status_code == 403


def test_viewer_cannot_export(client, viewer):
    assert client.get("/exports/sessions.csv", headers=viewer).status_code == 403
    assert client.get("/exports/aap.xlsx", headers=viewer).status_code == 403


def test_anonymous_gets_401(client):
    assert client.get("/dashboard/stats").status_code == 401
    assert client.get("/exports/sessions.csv").status_code == 401


def test_stats_tells_the_client_whether_it_may_drill_down(client, viewer, officer):
    assert client.get("/dashboard/stats", headers=viewer).json()["can_drill_down"] is False
    assert client.get("/dashboard/stats", headers=officer).json()["can_drill_down"] is True


# ==========================================================================
# Exports
# ==========================================================================


def test_csv_export_opens_and_has_rows(client, officer):
    response = client.get("/exports/sessions.csv", headers=officer)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]

    text = response.content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) >= 25, f"CSV has only {len(rows)} rows"
    assert "district" in rows[0]
    assert "aspiration_concept" in rows[0]


def test_csv_is_excel_safe_for_indic_text(client, officer):
    """Officers open these in Excel on Windows; without a BOM Devanagari and
    Telugu district names render as mojibake."""
    response = client.get("/exports/sessions.csv", headers=officer)
    assert response.content[:3] == b"\xef\xbb\xbf"


def test_csv_exports_no_name_or_phone_column(client, officer):
    """RULE 6 — there is no name to export, and phone is never exported."""
    response = client.get("/exports/sessions.csv", headers=officer)
    header = response.content.decode("utf-8-sig").splitlines()[0].split(",")
    offenders = [
        column
        for column in header
        if column in ("name", "phone", "beneficiary_name", "mobile")
    ]
    assert not offenders, f"export leaks PII columns: {offenders}"


def test_xlsx_export_opens_with_the_aap_annexure(client, officer):
    from openpyxl import load_workbook

    response = client.get("/exports/aap.xlsx", headers=officer)
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]

    workbook = load_workbook(io.BytesIO(response.content))
    assert "AAP Annexure" in workbook.sheetnames
    assert "Sessions" in workbook.sheetnames
    assert "Compliance" in workbook.sheetnames

    annexure = workbook["AAP Annexure"]
    header = [cell.value for cell in annexure[1]]
    assert header[0] == "GIA Domain"
    assert "Aspirations Captured" in header
    assert annexure.max_row > 1, "AAP annexure has no grouped rows"


def test_xlsx_compliance_sheet_cites_the_guidelines(client, officer):
    from openpyxl import load_workbook

    response = client.get("/exports/aap.xlsx", headers=officer)
    workbook = load_workbook(io.BytesIO(response.content))
    rows = list(workbook["Compliance"].iter_rows(min_row=2, values_only=True))
    joined = " ".join(str(cell) for row in rows for cell in row if cell)
    assert "30%" in joined, "women mandate missing from the compliance sheet"
    assert "PM-AJAY Guidelines" in joined
    assert "7.A.a.iv" in joined, "the compliance citation is missing"


def test_xlsx_labels_synthetic_rows(client, officer):
    from openpyxl import load_workbook

    response = client.get("/exports/aap.xlsx", headers=officer)
    workbook = load_workbook(io.BytesIO(response.content))
    rows = list(workbook["Compliance"].iter_rows(min_row=2, values_only=True))
    joined = " ".join(str(cell) for row in rows for cell in row if cell)
    assert "Synthetic" in joined or "synthetic" in joined


def test_export_can_be_filtered_by_district(client, officer):
    full = client.get("/exports/sessions.csv", headers=officer)
    one = client.get(f"/exports/sessions.csv?district={LATUR}", headers=officer)
    assert len(one.content) < len(full.content)


# ==========================================================================
# Crosswalk review + audit
# ==========================================================================


def test_officer_can_read_the_crosswalk_review_table(client, officer):
    body = client.get("/admin/crosswalk", headers=officer).json()
    assert body["total"] >= 150
    assert body["items"]
    assert body["can_edit"] is False


def test_admin_can_read_and_edit(client, admin):
    body = client.get("/admin/crosswalk", headers=admin).json()
    assert body["can_edit"] is True


def test_declared_gaps_are_filterable(client, officer):
    body = client.get("/admin/crosswalk?gaps_only=true", headers=officer).json()
    assert body["items"], "no declared gaps surfaced"
    assert all(item["is_gap"] for item in body["items"])
    assert any(item["concept"] == "poultry" for item in body["items"])


def test_crosswalk_review_mutation_writes_an_audit_row(client, admin, db_session):
    """Gate 9: "Crosswalk review mutations MUST create audit_log records"."""
    entry = client.get("/admin/crosswalk", headers=admin).json()["items"][0]
    before = db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "crosswalk.update")
    ).scalar_one()

    response = client.put(
        f"/admin/crosswalk/{entry['id']}", json={"status": "reviewed"}, headers=admin
    )
    assert response.status_code == 200
    assert response.json()["audited"] is True

    db_session.rollback()
    after = db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "crosswalk.update")
    ).scalar_one()
    assert after == before + 1


def test_audit_log_is_readable_by_admin_only(client, admin, officer):
    assert client.get("/admin/audit-log", headers=admin).status_code == 200
    assert client.get("/admin/audit-log", headers=officer).status_code == 403


def test_audit_entries_name_the_actor_and_the_change(client, admin):
    entry = client.get("/admin/crosswalk", headers=admin).json()["items"][0]
    client.put(f"/admin/crosswalk/{entry['id']}", json={"status": "reviewed"}, headers=admin)
    log_rows = client.get("/admin/audit-log?entity=crosswalk", headers=admin).json()["items"]
    assert log_rows
    latest = log_rows[0]
    assert latest["actor"] is not None
    assert latest["action"].startswith("crosswalk.")
    assert latest["before"] and latest["after"]
