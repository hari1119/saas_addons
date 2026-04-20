# -*- coding: utf-8 -*-
"""
Tests for the subscription lock screen logic.
Covers:
  - lock_status endpoint returns locked=False for admins
  - lock_status returns locked=True when company is locked
  - lock_status returns locked=False when active sub exists
  - is_saas_admin bypass
  - subscription_locked toggled correctly on state changes
"""
from datetime import date

from odoo.tests.common import HttpCase, TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'saas_lock')
class TestLockStatusEndpoint(HttpCase):
    """
    Integration tests via HTTP (requires a running Odoo server in test mode).
    Uses self.authenticate() from HttpCase to simulate logged-in users.
    """

    def setUp(self):
        super().setUp()
        self.plan = self.env['saas.subscription.type'].create({
            'name': 'Lock Test Plan',
            'plan_code': 'LOCK_TEST',
            'plan_level': 'gold',
            'duration_unit': 'months',
            'duration_value': 1,
            'price': 49.0,
            'grace_period_days': 3,
        })
        self.company = self.env['res.company'].create({'name': 'Lock Test Co'})

    def _call_lock_status(self):
        """Helper: POST to /saas/subscription/lock_status, return parsed JSON."""
        resp = self.url_open(
            '/saas/subscription/lock_status',
            data=b'{}',
            headers={'Content-Type': 'application/json'},
        )
        return resp.json().get('result', {})

    def test_admin_never_locked(self):
        """Odoo admin (uid=1) should always get locked=False."""
        self.authenticate('admin', 'admin')
        result = self._call_lock_status()
        self.assertFalse(result.get('locked'),
                         "Admin user must never be reported as locked.")

    def test_locked_company_returns_locked_true(self):
        """A regular user in a locked company should get locked=True."""
        # Create user in the locked company
        user = self.env['res.users'].create({
            'name': 'Locked User',
            'login': 'locked_user_test',
            'password': 'locked_user_test',
            'company_id': self.company.id,
            'company_ids': [(4, self.company.id)],
        })
        # Lock the company manually
        self.company.subscription_locked = True

        self.authenticate('locked_user_test', 'locked_user_test')
        result = self._call_lock_status()
        self.assertTrue(result.get('locked'),
                        "User in a locked company should get locked=True.")
        self.assertIn('support_email', result)

    def test_active_sub_returns_locked_false(self):
        """A user in a company with an active subscription should get locked=False."""
        user = self.env['res.users'].create({
            'name': 'Active User',
            'login': 'active_user_test',
            'password': 'active_user_test',
            'company_id': self.company.id,
            'company_ids': [(4, self.company.id)],
        })
        sub = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
            'state': 'active',
        })
        self.company.subscription_locked = False

        self.authenticate('active_user_test', 'active_user_test')
        result = self._call_lock_status()
        self.assertFalse(result.get('locked'))
        self.assertEqual(result.get('plan'), self.plan.name)


@tagged('saas_lock')
class TestLockScreenLogic(TransactionCase):
    """
    Unit tests for the Python-side lock logic (no HTTP needed).
    """

    def setUp(self):
        super().setUp()
        self.plan = self.env['saas.subscription.type'].create({
            'name': 'Logic Test Plan',
            'plan_code': 'LOGIC_TEST',
            'plan_level': 'silver',
            'duration_unit': 'months',
            'duration_value': 3,
            'price': 30.0,
            'grace_period_days': 5,
        })
        self.company = self.env['res.company'].create({'name': 'Logic Test Co'})

    def test_subscription_locked_false_when_active(self):
        sub = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
        })
        sub.action_confirm()   # → active
        self.assertFalse(
            self.company.subscription_locked,
            "Company must NOT be locked when an active subscription exists."
        )

    def test_subscription_locked_true_when_expired(self):
        sub = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
            'state': 'active',
        })
        sub.action_expire()
        self.assertTrue(
            self.company.subscription_locked,
            "Company MUST be locked when subscription is expired."
        )

    def test_subscription_locked_true_when_cancelled(self):
        sub = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
            'state': 'active',
        })
        sub.action_cancel()
        self.assertTrue(self.company.subscription_locked)

    def test_subscription_locked_false_when_grace(self):
        """Grace period = still accessible, so locked should be False."""
        sub = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
            'state': 'grace',
        })
        sub._sync_company_lock()
        self.assertFalse(
            self.company.subscription_locked,
            "Company must NOT be locked during grace period."
        )

    def test_subscription_locked_false_when_trial(self):
        """Trial = accessible, so locked should be False."""
        sub = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
            'state': 'trial',
        })
        sub._sync_company_lock()
        self.assertFalse(self.company.subscription_locked)

    def test_saas_admin_field_exists(self):
        """is_saas_admin field must exist on res.users."""
        admin = self.env['res.users'].browse(self.env.ref('base.user_admin').id)
        self.assertIn('is_saas_admin', admin._fields)

    def test_renew_unlocks_company(self):
        sub = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
            'state': 'expired',
        })
        sub._sync_company_lock()
        self.assertTrue(self.company.subscription_locked)

        sub.action_renew()
        self.assertFalse(
            self.company.subscription_locked,
            "Renewing a subscription must unlock the company."
        )

    def test_multiple_companies_independent(self):
        """Locking one company must not affect another."""
        company_b = self.env['res.company'].create({'name': 'Company B'})

        sub_a = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': self.company.id,
            'start_date': date.today(),
            'state': 'active',
        })
        sub_b = self.env['saas.subscription'].create({
            'type_id': self.plan.id,
            'company_id': company_b.id,
            'start_date': date.today(),
            'state': 'active',
        })

        sub_a.action_expire()   # lock company A

        self.assertTrue(self.company.subscription_locked,
                        "Company A should be locked.")
        self.assertFalse(company_b.subscription_locked,
                         "Company B must remain unlocked.")
