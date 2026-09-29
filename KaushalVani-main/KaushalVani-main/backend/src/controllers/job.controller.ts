import { Request, Response } from 'express';
import { store } from '../db/store';

export const getJobs = (req: Request, res: Response) => {
  const { sector, district, search } = req.query;
  let jobs = Array.from(store.employmentOpportunities.values());

  if (sector && sector !== 'All') {
    jobs = jobs.filter(j => j.sector.toLowerCase().includes((sector as string).toLowerCase()));
  }
  if (district && district !== 'All') {
    jobs = jobs.filter(j => j.district.toLowerCase().includes((district as string).toLowerCase()));
  }
  if (search) {
    const qStr = (search as string).toLowerCase();
    jobs = jobs.filter(j => j.title.toLowerCase().includes(qStr) || j.employer.toLowerCase().includes(qStr));
  }

  res.json({ jobs, total: jobs.length });
};

export const getEnterprisePathways = (req: Request, res: Response) => {
  const { sector } = req.query;
  let enterprises = Array.from(store.enterprisePathways.values());

  if (sector && sector !== 'All') {
    enterprises = enterprises.filter(e => e.sector.toLowerCase().includes((sector as string).toLowerCase()));
  }

  res.json({ enterprisePathways: enterprises });
};
