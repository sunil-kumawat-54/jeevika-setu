import { Request, Response } from 'express';
import { store } from '../db/store';

export const getQualifications = (req: Request, res: Response) => {
  const { sector, nsqfLevel, search } = req.query;
  let qualList = Array.from(store.qualifications.values());

  if (sector && sector !== 'All') {
    qualList = qualList.filter(q => q.sector.toLowerCase().includes((sector as string).toLowerCase()));
  }
  if (nsqfLevel) {
    qualList = qualList.filter(q => q.nsqf_level === Number(nsqfLevel));
  }
  if (search) {
    const qStr = (search as string).toLowerCase();
    qualList = qualList.filter(q => 
      q.job_role.toLowerCase().includes(qStr) || 
      q.qp_code.toLowerCase().includes(qStr) || 
      q.skills.some(s => s.toLowerCase().includes(qStr))
    );
  }

  res.json({ qualifications: qualList, total: qualList.length });
};

export const getQualificationById = (req: Request, res: Response) => {
  const { id } = req.params;
  const qual = store.qualifications.get(id);

  if (!qual) {
    return res.status(404).json({ error: 'Qualification record not found' });
  }

  res.json({ qualification: qual });
};
