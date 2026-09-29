import { Request, Response } from 'express';
import { store } from '../db/store';

export const updateOutcome = (req: Request, res: Response) => {
  const { id } = req.params;
  const { training_status, completion_date, certification_status, employment_status, enterprise_status, placement_date, income_band, feedback } = req.body;

  let outcome = store.outcomes.get(id);

  if (!outcome) {
    // Find outcome by beneficiary_id if id matches beneficiary
    const found = Array.from(store.outcomes.values()).find(o => o.beneficiary_id === id);
    if (found) {
      outcome = found;
    } else {
      return res.status(404).json({ error: 'Outcome record not found' });
    }
  }

  if (training_status) outcome.training_status = training_status;
  if (completion_date) outcome.completion_date = completion_date;
  if (certification_status) outcome.certification_status = certification_status;
  if (employment_status) outcome.employment_status = employment_status;
  if (enterprise_status) outcome.enterprise_status = enterprise_status;
  if (placement_date) outcome.placement_date = placement_date;
  if (income_band) outcome.income_band = income_band;
  if (feedback) outcome.feedback = feedback;
  outcome.last_updated = new Date().toISOString();

  // Also update beneficiary status if placed/enrolled
  const beneficiary = store.beneficiaries.get(outcome.beneficiary_id);
  if (beneficiary) {
    if (employment_status === 'Wage Employed') beneficiary.status = 'placed';
    else if (enterprise_status === 'Operational') beneficiary.status = 'self_employed';
    else if (training_status === 'Enrolled' || training_status === 'In Progress') beneficiary.status = 'enrolled';
  }

  res.json({ success: true, outcome });
};

export const getOutcomeByBeneficiary = (req: Request, res: Response) => {
  const { beneficiaryId } = req.params;
  const outcome = Array.from(store.outcomes.values()).find(o => o.beneficiary_id === beneficiaryId);

  if (!outcome) {
    return res.status(404).json({ error: 'Outcome record not found' });
  }

  res.json({ outcome });
};
