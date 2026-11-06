# GitHub Billing Settings - Visual Reference

## Where to Find Your Billing Settings

### Option 1: Direct URLs (Easiest)
Copy and paste these directly into your browser:

**Update Spending Limit (DO THIS FIRST):**
```
https://github.com/settings/billing/spending_limits
```

**Check Overview:**
```
https://github.com/settings/billing/overview
```

**Update Payment Method:**
```
https://github.com/settings/billing/payment_information
```

---

### Option 2: Navigate via GitHub UI

1. Click your **profile icon** (top-right corner)
2. Select **"Settings"**
3. In left sidebar, look for **"Billing and plans"** section
4. Click **"Billing and plans"**
5. You'll see:
   - Overview tab
   - Spending limits tab
   - Billing history tab
   - Sponsors tab

---

## What You Should See: Spending Limits Page

### Current Status (Before Fix)
```
GitHub Actions
├─ Current Limit: $0 or $[some amount]
├─ Current Usage: $[amount] (EXCEEDED or very high)
└─ Status: ⚠️ BLOCKED
```

### What to Change
On the spending limits page, look for this section:

```
┌─────────────────────────────────────────────────┐
│ GitHub Actions spending limit                   │
│                                                  │
│ Set spending limit for GitHub Actions:          │
│                                                  │
│ Current: $[current amount]                      │
│ New:     [ $20 ▼ ]  [UPDATE button]             │
│                                                  │
│ Included amount: $0                             │
│ Previous billing period usage: $X.XX            │
└─────────────────────────────────────────────────┘
```

**What to do:**
1. Click the dropdown showing current amount
2. Select a new amount:
   - Recommended: $20, $50, or $100
   - Can also select "Unlimited" if available
3. Click **UPDATE** button
4. ✅ Done!

---

## What You Should See: Overview Page

### Current Status Indicator
Look for the **GitHub Actions** card showing:

```
┌────────────────────────────────┐
│ GitHub Actions                 │
├────────────────────────────────┤
│ Usage this month: $X.XX        │
│ Spending limit: $Y             │
│                                │
│ [Progress bar]                 │
│ $X.XX / $Y                     │
│                                │
│ ✅ Within limit   OR            │
│ ⚠️  EXCEEDED  OR                │
│ 🔴 Blocked by billing          │
└────────────────────────────────┘
```

**Healthy:** $X.XX / $50 (shows you have room)
**Warning:** $45 / $50 (close to limit)
**Problem:** EXCEEDED or shows error message (this is what we're fixing)

---

## What You Should See: Payment Method Page

### Current Payment Status

You should see a card like:

```
┌────────────────────────────────────────────────┐
│ Payment method                                 │
├────────────────────────────────────────────────┤
│ Active payment method:                         │
│                                                │
│ Visa ending in 1234                           │
│ Expires: 12/2026                              │
│                                                │
│ ✅ Active and valid  OR                       │
│ ⚠️  FAILED or EXPIRED  OR                     │
│ 🔴 Action required                            │
│                                                │
│ [UPDATE PAYMENT METHOD] button                 │
│                                                │
│ Next billing date: November 15, 2026          │
└────────────────────────────────────────────────┘
```

**If you see ⚠️ or 🔴:**
1. Click **UPDATE PAYMENT METHOD**
2. Enter your credit card info
3. Make sure expiration date hasn't passed
4. Click **UPDATE**
5. ✅ Fixed!

---

## Quick Decision Tree

```
Go to: https://github.com/settings/billing/overview

Does it show "EXCEEDED" or error message?
│
├─ YES (Exceeded) ─────→ Go to spending_limits
│                         Change limit from $X to $50+
│                         Click UPDATE
│                         ✅ DONE
│
└─ NO (Shows warning) ──→ Check payment method
                          Click "Update payment method"
                          Re-enter credit card
                          Click UPDATE
                          ✅ DONE

After either fix:
Wait 2-5 minutes → Check again
Should show ✅ ACTIVE and within limit
```

---

## Before vs. After

### BEFORE (Problem State)
```
GitHub Actions Status: ❌ BLOCKED

- Spending Limit: $0 or $[low amount]
- Current Usage: EXCEEDED
- Payment Method: ⚠️ FAILED or ⚠️ EXPIRED
- Job Status: Jobs not starting (billing issue)
```

### AFTER (Fixed State)
```
GitHub Actions Status: ✅ ACTIVE

- Spending Limit: $20-$100 (your choice)
- Current Usage: Under limit
- Payment Method: ✅ VALID
- Job Status: Jobs running normally
```

---

## Timeline After You Fix It

```
You update billing settings
         ↓
      (2 min) GitHub detects update
         ↓
      (5 min) CI starts retrying failed jobs
         ↓
     (15 min) Tests and builds complete
         ↓
      (2 min) Auto-merge kicks in
         ↓
  ✅ All 11 PRs merged successfully!
         ↓
     (5 min) Day 5 OAuth deployed to main
```

**Total time from fix to complete: ~30 minutes**

---

## Support

### If you need help:

1. **GitHub Documentation:**
   - https://docs.github.com/en/billing

2. **GitHub Community Forum:**
   - https://github.community

3. **GitHub Support:**
   - https://support.github.com
   - Email: support@github.com

4. **This Repository:**
   - See: `PR_MERGE_STATUS.md` for full technical details
   - See: `BILLING_FIX_GUIDE.md` for step-by-step instructions

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Can't find billing settings | Use direct URL: https://github.com/settings/billing/overview |
| Payment method shows failed | Click "Update" and re-enter card details |
| Spending limit dropdown empty | Refresh page or try different browser |
| Still seeing errors after update | Wait 5 minutes and refresh (GitHub needs time to propagate) |
| Card keeps getting declined | Contact your bank - they may block GitHub transactions |
| Multiple payment methods | Select the working one or add a new card |

---

## That's it! 🎉

You're just 2-5 minutes away from fixing everything!

1. Go to: **https://github.com/settings/billing/spending_limits**
2. Change limit to **$20-50**
3. Click **UPDATE**
4. Wait 5 minutes
5. All PRs merge automatically

You've got this! 💪
