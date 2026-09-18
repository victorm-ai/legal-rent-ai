"""Remove test data created by the default lawyer user."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from config.settings import get_settings
from data.database import get_connection

LAWYER_EMAIL = "abogado@contractes.com"


def main() -> int:
    with get_connection(get_settings()) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT u.id
            FROM app.users u
            JOIN app.roles r ON r.id = u.role_id
            WHERE u.email = ? AND r.code = N'lawyer'
            """,
            LAWYER_EMAIL,
        )
        row = cursor.fetchone()
        if row is None:
            print(f"Lawyer not found: {LAWYER_EMAIL}")
            return 1

        lawyer_id = str(row[0])
        print(f"Cleaning lawyer data for {LAWYER_EMAIL} ({lawyer_id})")

        cursor.execute(
            "SELECT analysis_id FROM app.analysis_approvals WHERE lawyer_id = ?",
            lawyer_id,
        )
        approved_analysis_ids = [str(item[0]) for item in cursor.fetchall()]

        cursor.execute(
            """
            SELECT DISTINCT f.analysis_id
            FROM app.finding_reviews fr
            JOIN app.findings f ON f.id = fr.finding_id
            WHERE fr.lawyer_id = ?
            """,
            lawyer_id,
        )
        reviewed_analysis_ids = [str(item[0]) for item in cursor.fetchall()]
        affected_analysis_ids = sorted(set(approved_analysis_ids + reviewed_analysis_ids))

        cursor.execute("DELETE FROM app.finding_reviews WHERE lawyer_id = ?", lawyer_id)
        print(f"Deleted finding_reviews: {cursor.rowcount}")

        cursor.execute("DELETE FROM app.analysis_approvals WHERE lawyer_id = ?", lawyer_id)
        print(f"Deleted analysis_approvals: {cursor.rowcount}")

        cursor.execute("DELETE FROM app.review_messages WHERE user_id = ?", lawyer_id)
        print(f"Deleted review_messages: {cursor.rowcount}")

        if affected_analysis_ids:
            placeholders = ",".join("?" for _ in affected_analysis_ids)
            cursor.execute(
                f"""
                UPDATE app.analyses
                SET status = N'pending_review'
                WHERE id IN ({placeholders})
                  AND status IN (N'approved', N'reviewed')
                """,
                affected_analysis_ids,
            )
            print(f"Reset lawyer-touched analyses: {cursor.rowcount}")

        cursor.execute(
            """
            UPDATE app.contract_documents
            SET extraction_method = N'native'
            WHERE extraction_method = N'edited'
            """
        )
        print(f"Reset edited document markers: {cursor.rowcount}")

        connection.commit()
        print("Done.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
