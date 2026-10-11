import unittest
from streamlit.testing.v1 import AppTest
from analysis import load_data, align_weeks, correlations

class AnalysisTests(unittest.TestCase):
    def test_alignment_and_missing_exposure(self):
        psi, visits = load_data()
        weeks = align_weeks(psi, visits)
        self.assertEqual(weeks.loc[weeks.eligible, 'epi_week'].tolist(), [36,37,38,39])
        self.assertEqual(weeks.observations.tolist(), [0,115,161,161,159,161])
        self.assertTrue(weeks.loc[0, ['mean_psi','max_psi','unhealthy_pct']].isna().all())
        self.assertFalse(weeks.complete.any())
        self.assertAlmostEqual(correlations(weeks).iloc[0]['Pearson r'], .611180, places=4)
        lagged = align_weeks(psi, visits, lag=1)
        self.assertEqual(lagged.loc[lagged.eligible, 'epi_week'].tolist(), [37,38,39])
        self.assertEqual(correlations(lagged).iloc[0]['Weeks'], 3)

    def test_dashboard_controls(self):
        app = AppTest.from_file('app.py').run(timeout=30)
        self.assertFalse(app.exception)
        app.selectbox[0].set_value(1).run()
        self.assertFalse(app.exception)
        app.checkbox[0].check().run()
        self.assertFalse(app.exception)
        app.radio[0].set_value('Daily averages').run()
        self.assertFalse(app.exception)
        app.multiselect[0].set_value([]).run()
        self.assertFalse(app.exception)

if __name__ == '__main__':
    unittest.main()
