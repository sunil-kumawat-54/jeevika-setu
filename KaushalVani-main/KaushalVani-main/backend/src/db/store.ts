import { randomUUID } from 'crypto';

export interface Beneficiary {
  id: string;
  name: string;
  age: number;
  gender: string;
  location: string;
  district: string;
  state: string;
  pincode: string;
  language: string;
  education: string;
  current_occupation: string;
  previous_occupation?: string;
  family_occupation?: string;
  existing_skills: string[];
  experience_years: number;
  desired_occupation: string;
  interests: string[];
  employment_preference: 'wage' | 'self_employment' | 'either';
  mobility_km: number;
  physical_constraints?: string;
  digital_literacy: 'basic' | 'intermediate' | 'advanced' | 'none';
  income_category?: string;
  status: 'draft' | 'profiled' | 'analyzed' | 'enrolled' | 'placed' | 'self_employed';
  created_at: string;
}

export interface Qualification {
  id: string;
  qp_code: string;
  job_role: string;
  sector: string;
  nsqf_level: number;
  eligibility: string;
  education_req: string;
  experience_req: string;
  duration_hours: number;
  skills: string[];
  nos_modules: string[];
  progression: string;
  awarding_body: string;
  source_url: string;
  source_name: string;
  last_verified_at: string;
}

export interface TrainingCentre {
  id: string;
  provider_name: string;
  centre_name: string;
  district: string;
  state: string;
  address: string;
  lat: number;
  lng: number;
  contact_phone: string;
  contact_email: string;
  courses: string[];
  source_url: string;
}

export interface EmploymentOpportunity {
  id: string;
  title: string;
  employer: string;
  sector: string;
  district: string;
  state: string;
  lat: number;
  lng: number;
  salary_range: string;
  experience_req: string;
  education_req: string;
  vacancies: number;
  job_type: string;
  verified: boolean;
  source_url: string;
}

export interface EnterprisePathway {
  id: string;
  title: string;
  sector: string;
  suitable_for_skills: string[];
  min_education: string;
  equipment_required: string[];
  target_market: string;
  estimated_investment: string;
  potential_revenue: string;
  key_steps: string[];
  guidance_url: string;
}

export interface RecommendationFactor {
  factor: string;
  score: number;
  description: string;
}

export interface Recommendation {
  id: string;
  beneficiary_id: string;
  qualification_id: string;
  score: number;
  match_reasons: string[];
  factors: RecommendationFactor[];
  skill_gap: {
    required_skills: string[];
    existing_skills: string[];
    missing_skills: string[];
    gap_severity: 'Low' | 'Moderate' | 'High';
  };
  nearby_centres: {
    centre: TrainingCentre;
    distance_km: number;
  }[];
  employment_pathways: EmploymentOpportunity[];
  enterprise_pathways: EnterprisePathway[];
  created_at: string;
}

export interface Roadmap {
  id: string;
  beneficiary_id: string;
  recommendation_id: string;
  qualification_id: string;
  pathway_type: 'wage' | 'self_employment' | 'combined';
  title: string;
  steps: {
    step_number: number;
    title: string;
    description: string;
    duration?: string;
    details?: string;
  }[];
  explanation: string;
  created_at: string;
}

export interface Outcome {
  id: string;
  beneficiary_id: string;
  training_status: 'Not Started' | 'Enrolled' | 'In Progress' | 'Completed' | 'Dropped Out';
  completion_date?: string;
  certification_status: 'Pending' | 'Certified' | 'Not Certified';
  employment_status: 'Unemployed' | 'Wage Employed' | 'Self Employed' | 'Apprentice';
  enterprise_status: 'None' | 'Planning' | 'Operational';
  placement_date?: string;
  income_band?: string;
  feedback?: string;
  last_updated: string;
}

export class InMemoryStore {
  public beneficiaries: Map<string, Beneficiary> = new Map();
  public qualifications: Map<string, Qualification> = new Map();
  public trainingCentres: Map<string, TrainingCentre> = new Map();
  public employmentOpportunities: Map<string, EmploymentOpportunity> = new Map();
  public enterprisePathways: Map<string, EnterprisePathway> = new Map();
  public recommendations: Map<string, Recommendation> = new Map();
  public roadmaps: Map<string, Roadmap> = new Map();
  public outcomes: Map<string, Outcome> = new Map();

  constructor() {
    this.seed();
  }

  private seed() {
    // 1. Seed Qualifications (Official NQR reference items)
    const seedQualifications: Qualification[] = [
      {
        id: 'qual-001',
        qp_code: 'ELE/Q5901',
        job_role: 'Solar PV System Installer',
        sector: 'Electronics & Hardware',
        nsqf_level: 4,
        eligibility: '10th Class Pass',
        education_req: '10th Class Pass',
        experience_req: '0-1 year basic electrical knowledge helpful',
        duration_hours: 350,
        skills: ['Solar Panel Assembly', 'Electrical Wiring', 'Inverter Connection', 'Battery Storage Setup', 'Safety Standards', 'Multimeter Usage'],
        nos_modules: ['ELE/N5901 - Site Survey', 'ELE/N5902 - System Installation', 'ELE/N5903 - Maintenance & Testing'],
        progression: 'Solar System Technician -> Solar Site Engineer',
        awarding_body: 'Electronics Sector Skills Council of India (ESSCI)',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=ELE/Q5901',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-01-15'
      },
      {
        id: 'qual-002',
        qp_code: 'ELE/Q6001',
        job_role: 'Field Technician - Domestic Appliances',
        sector: 'Electronics & Hardware',
        nsqf_level: 4,
        eligibility: '10th Class Pass',
        education_req: '10th Class Pass',
        experience_req: '0 years',
        duration_hours: 300,
        skills: ['Circuit Troubleshooting', 'Appliance Repair', 'Soldering', 'Customer Handling', 'Voltage Testing'],
        nos_modules: ['ELE/N6001 - Diagnose Appliance Defect', 'ELE/N6002 - Repair Components'],
        progression: 'Senior Field Technician -> Service Centre Supervisor',
        awarding_body: 'ESSCI',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=ELE/Q6001',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-01-15'
      },
      {
        id: 'qual-003',
        qp_code: 'AMH/Q0301',
        job_role: 'Self Employed Tailor / Custom Garment Maker',
        sector: 'Apparel',
        nsqf_level: 4,
        eligibility: '8th Class Pass',
        education_req: '8th Class Pass',
        experience_req: 'Basic hand stitching or home tailoring experience',
        duration_hours: 340,
        skills: ['Pattern Making', 'Garment Cutting', 'Machine Stitching', 'Measurement Taking', 'Quality Finishing', 'Costing & Pricing'],
        nos_modules: ['AMH/N0301 - Draft Pattern', 'AMH/N0302 - Stitch Garment', 'AMH/N0303 - Inspect & Finish'],
        progression: 'Boutique Owner -> Master Cutter',
        awarding_body: 'Apparel Made-ups & Home Furnishing Sector Skill Council',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=AMH/Q0301',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-01-10'
      },
      {
        id: 'qual-004',
        qp_code: 'AGR/Q0801',
        job_role: 'Organic Farming Farmer & Micro Entrepreneur',
        sector: 'Agriculture',
        nsqf_level: 4,
        eligibility: '5th Class Pass',
        education_req: '5th Class Pass / Literacy',
        experience_req: 'Traditional farming background',
        duration_hours: 240,
        skills: ['Bio-fertilizer Preparation', 'Composting', 'Organic Pest Management', 'Soil Health Testing', 'Direct Marketing', 'Drip Irrigation Setup'],
        nos_modules: ['AGR/N0801 - Soil Preparation', 'AGR/N0802 - Bio Input Production', 'AGR/N0803 - Harvesting & Direct Sale'],
        progression: 'Organic FPO Lead -> Agri Enterprise Founder',
        awarding_body: 'Agriculture Skill Council of India (ASCI)',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=AGR/Q0801',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-02-01'
      },
      {
        id: 'qual-005',
        qp_code: 'SSC/Q2212',
        job_role: 'Domestic Data Entry Operator',
        sector: 'IT-ITeS',
        nsqf_level: 4,
        eligibility: '10th Class Pass',
        education_req: '10th Class Pass',
        experience_req: 'Basic computer literacy',
        duration_hours: 400,
        skills: ['Keyboard Typing (30 wpm)', 'MS Office / Google Docs', 'Data Verification', 'Spreadsheet Handling', 'Basic English Comprehension'],
        nos_modules: ['SSC/N2212 - Transcribe Data', 'SSC/N2213 - Verify Data Accuracy'],
        progression: 'Senior Data Entry Operator -> Office Administrator',
        awarding_body: 'IT-ITeS SSC NASSCOM',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=SSC/Q2212',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-01-20'
      },
      {
        id: 'qual-006',
        qp_code: 'ASC/Q1401',
        job_role: 'Auto Service Technician (2-Wheeler / 3-Wheeler)',
        sector: 'Automotive',
        nsqf_level: 4,
        eligibility: '8th Class Pass',
        education_req: '8th Class Pass',
        experience_req: '0-1 year workshop helper experience',
        duration_hours: 360,
        skills: ['Engine Overhaul', 'Brake Servicing', 'Electrical Diagnostic', 'Oil Changing', 'Tire Balancing'],
        nos_modules: ['ASC/N1401 - Engine Diagnostics', 'ASC/N1402 - Transmission Servicing'],
        progression: 'Master Mechanic -> Garage Owner',
        awarding_body: 'Automotive Skills Development Council (ASDC)',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=ASC/Q1401',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-01-18'
      },
      {
        id: 'qual-007',
        qp_code: 'HSS/Q5101',
        job_role: 'General Duty Assistant / Healthcare Attendant',
        sector: 'Healthcare',
        nsqf_level: 4,
        eligibility: '10th Class Pass',
        education_req: '10th Class Pass',
        experience_req: 'None required',
        duration_hours: 480,
        skills: ['Patient Care', 'Vital Signs Monitoring', 'Hygiene Management', 'First Aid', 'Patient Transport', 'Basic Medical Terminology'],
        nos_modules: ['HSS/N5101 - Assist Patient Daily Care', 'HSS/N5102 - Monitor Patient Vitals'],
        progression: 'Senior Nursing Assistant -> Patient Care Supervisor',
        awarding_body: 'Healthcare Sector Skill Council (HSSC)',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=HSS/Q5101',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-02-05'
      },
      {
        id: 'qual-008',
        qp_code: 'CON/Q0602',
        job_role: 'Assistant Electrician - Construction',
        sector: 'Construction',
        nsqf_level: 3,
        eligibility: '8th Class Pass',
        education_req: '8th Class Pass',
        experience_req: '0 years',
        duration_hours: 320,
        skills: ['Conduit Fitting', 'House Wiring', 'Distribution Board Assembly', 'Earthing Installation', 'Safety Gear Operations'],
        nos_modules: ['CON/N0602 - Lay Wiring Conduits', 'CON/N0603 - Install DB & Switchboards'],
        progression: 'Building Electrician -> Electrical Contractor',
        awarding_body: 'Construction Skill Development Council of India (CSDCI)',
        source_url: 'https://nqr.gov.in/qualification-title?qCode=CON/Q0602',
        source_name: 'National Qualification Register (NQR)',
        last_verified_at: '2026-01-25'
      }
    ];

    seedQualifications.forEach(q => this.qualifications.set(q.id, q));

    // 2. Seed Training Centres (Locations centered near Aurangabad & Western Maharashtra region)
    const seedCentres: TrainingCentre[] = [
      {
        id: 'tc-101',
        provider_name: 'PMKVK Government ITI Aurangabad',
        centre_name: 'Chhatrapati Sambhajinagar Skill Training Hub',
        district: 'Aurangabad (Chhatrapati Sambhajinagar)',
        state: 'Maharashtra',
        address: 'MIDC Chikalthana, Industrial Area, Aurangabad - 431006',
        lat: 19.8833,
        lng: 75.3833,
        contact_phone: '+91 240 2484920',
        contact_email: 'iti.aurangabad@dvet.gov.in',
        courses: ['qual-001', 'qual-002', 'qual-006', 'qual-008'],
        source_url: 'https://skillindia.gov.in/centre/tc-101'
      },
      {
        id: 'tc-102',
        provider_name: 'Jan Shikshan Sansthan (JSS) Aurangabad',
        centre_name: 'JSS Community Livelihood Skill Centre',
        district: 'Aurangabad (Chhatrapati Sambhajinagar)',
        state: 'Maharashtra',
        address: 'Near Kranti Chowk, Station Road, Aurangabad - 431001',
        lat: 19.8762,
        lng: 75.3235,
        contact_phone: '+91 240 2331144',
        contact_email: 'jss.aurangabad@gmail.com',
        courses: ['qual-003', 'qual-004', 'qual-005'],
        source_url: 'https://jss.gov.in/centre/aurangabad'
      },
      {
        id: 'tc-103',
        provider_name: 'MSSDS Solar Vocational Training Institute',
        centre_name: 'Marathwada Renewable Energy Skill Academy',
        district: 'Aurangabad (Chhatrapati Sambhajinagar)',
        state: 'Maharashtra',
        address: 'Waluj MIDC Sector 3, Aurangabad - 431136',
        lat: 19.8398,
        lng: 75.2411,
        contact_phone: '+91 240 2554099',
        contact_email: 'info@mresa.org.in',
        courses: ['qual-001', 'qual-008'],
        source_url: 'https://kaushalya.mahasarkar.co.in'
      },
      {
        id: 'tc-104',
        provider_name: 'Rural Self Employment Training Institute (RSETI)',
        centre_name: 'Bank of Maharashtra RSETI Centre',
        district: 'Jalna',
        state: 'Maharashtra',
        address: 'Devalgaon Raja Road, Jalna - 431203',
        lat: 19.8415,
        lng: 75.8864,
        contact_phone: '+91 2482 220199',
        contact_email: 'rseti.jalna@mahabank.co.in',
        courses: ['qual-003', 'qual-004', 'qual-006'],
        source_url: 'https://nseret.in/rseti/jalna'
      },
      {
        id: 'tc-105',
        provider_name: 'District Healthcare Skill Centre',
        centre_name: 'Government Hospital Nursing Training Wing',
        district: 'Aurangabad (Chhatrapati Sambhajinagar)',
        state: 'Maharashtra',
        address: 'Ghati Hospital Campus, Panchakki Road, Aurangabad - 431001',
        lat: 19.8912,
        lng: 75.3188,
        contact_phone: '+91 240 2402100',
        contact_email: 'gda.training@ghati.gov.in',
        courses: ['qual-007'],
        source_url: 'https://arogya.maharashtra.gov.in'
      }
    ];

    seedCentres.forEach(c => this.trainingCentres.set(c.id, c));

    // 3. Seed Employment Opportunities
    const seedJobs: EmploymentOpportunity[] = [
      {
        id: 'job-201',
        title: 'Junior Solar Installation Technician',
        employer: 'SunPower Marathwada Energy Solutions',
        sector: 'Electronics / Renewable Energy',
        district: 'Aurangabad (Chhatrapati Sambhajinagar)',
        state: 'Maharashtra',
        lat: 19.8700,
        lng: 75.3400,
        salary_range: '₹14,000 - ₹18,000 / month',
        experience_req: '0-1 year after NSQF Level 4 training',
        education_req: '10th Pass + Solar PV Installer Certificate',
        vacancies: 12,
        job_type: 'Full-Time Wage Employment',
        verified: true,
        source_url: 'https://ncs.gov.in/job/job-201'
      },
      {
        id: 'job-202',
        title: 'Residential Electrical Maintenance Worker',
        employer: 'MSEDCL Contractors Co-op Society',
        sector: 'Construction & Utilities',
        district: 'Aurangabad (Chhatrapati Sambhajinagar)',
        state: 'Maharashtra',
        lat: 19.8800,
        lng: 75.3300,
        salary_range: '₹12,000 - ₹16,000 / month',
        experience_req: 'Freshers welcome with Assistant Electrician cert',
        education_req: '8th Pass + ITI / NSQF Certificate',
        vacancies: 8,
        job_type: 'Contractual / Wage Employment',
        verified: true,
        source_url: 'https://ncs.gov.in/job/job-202'
      },
      {
        id: 'job-203',
        title: 'Apparel Sewing Machine Operator',
        employer: 'Bajaj Garment Cluster Unit',
        sector: 'Apparel & Textile',
        district: 'Waluj, Aurangabad',
        state: 'Maharashtra',
        lat: 19.8350,
        lng: 75.2400,
        salary_range: '₹11,000 - ₹15,000 / month',
        experience_req: 'Basic tailoring certification',
        education_req: '8th Pass',
        vacancies: 25,
        job_type: 'Full-Time Wage Employment',
        verified: true,
        source_url: 'https://ncs.gov.in/job/job-203'
      },
      {
        id: 'job-204',
        title: 'Patient Care General Duty Assistant',
        employer: 'Apex Multispecialty Hospital',
        sector: 'Healthcare',
        district: 'Aurangabad',
        state: 'Maharashtra',
        lat: 19.8780,
        lng: 75.3200,
        salary_range: '₹13,500 - ₹17,500 / month',
        experience_req: 'GDA NSQF Level 4 Certificate',
        education_req: '10th Pass',
        vacancies: 6,
        job_type: 'Shift-based Wage Employment',
        verified: true,
        source_url: 'https://ncs.gov.in/job/job-204'
      }
    ];

    seedJobs.forEach(j => this.employmentOpportunities.set(j.id, j));

    // 4. Seed Enterprise Pathways
    const seedEnterprises: EnterprisePathway[] = [
      {
        id: 'ent-301',
        title: 'Village Solar Repair & Charging Enterprise',
        sector: 'Renewable Energy',
        suitable_for_skills: ['Solar Wiring', 'Battery Repair', 'Inverter Servicing', 'Electrical Wiring'],
        min_education: '10th Pass + NSQF Solar Certification',
        equipment_required: ['Digital Multimeter', 'Soldering Kit', 'Tool Set', 'Solar Testing Meter'],
        target_market: 'Rural households, farmers with solar pumps, small commercial shops',
        estimated_investment: '₹25,000 - ₹40,000 (Eligible for PM-AJAY GIA / PMEGP loan subsidy)',
        potential_revenue: '₹18,000 - ₹28,000 / month',
        key_steps: [
          'Complete 3-month Solar PV Installer Certification',
          'Apply for PM-AJAY Grant-in-Aid (GIA) micro-enterprise support',
          'Procure basic diagnostic toolkit and spare connectors',
          'Register on local Panchayat & Agri-Coop service directory',
          'Begin rooftop maintenance & solar pump troubleshooting service'
        ],
        guidance_url: 'https://pmajay.gov.in/gia/enterprise-guidelines'
      },
      {
        id: 'ent-302',
        title: 'Custom Tailoring & Readymade Alteration Centre',
        sector: 'Apparel & Fashion',
        suitable_for_skills: ['Garment Stitching', 'Pattern Cutting', 'Measurement Taking', 'Costing'],
        min_education: '8th Pass + Tailoring Certification',
        equipment_required: ['Single-needle Industrial Sewing Machine', 'Cutting Table', 'Ironing Press'],
        target_market: 'Local village community, school uniform orders, festive wear orders',
        estimated_investment: '₹15,000 - ₹30,000 (Supported under PM-AJAY GIA Micro-grant)',
        potential_revenue: '₹14,000 - ₹22,000 / month',
        key_steps: [
          'Finish Self Employed Tailor course at JSS or RSETI',
          'Procure motor-operated sewing machine',
          'Tie up with local school committees for bulk uniform orders',
          'Establish doorstep alteration service for nearby weekly markets'
        ],
        guidance_url: 'https://pmajay.gov.in/gia/tailoring-unit'
      },
      {
        id: 'ent-303',
        title: 'Organic Bio-Input & Vermicompost Production Unit',
        sector: 'Agriculture & Bio-Products',
        suitable_for_skills: ['Bio-fertilizer Preparation', 'Composting', 'Organic Farming'],
        min_education: '5th Pass / Farmer Literacy',
        equipment_required: ['Composting Pits / Beds', 'Bio-inoculant Starters', 'Packaging Bags', 'Sieve Shaker'],
        target_market: 'Local farmers, horticultural crop growers, home garden enthusiasts',
        estimated_investment: '₹20,000 - ₹35,000 (Subsidy up to 50% via PM-AJAY)',
        potential_revenue: '₹16,000 - ₹26,000 / month',
        key_steps: [
          'Complete ASCI Organic Farmer Module',
          'Set up 4 vermicompost beds using agricultural waste',
          'Obtain District Organic Certification / FPO membership',
          'Supply enriched bio-manure to local farmer networks'
        ],
        guidance_url: 'https://pmajay.gov.in/gia/agri-enterprise'
      }
    ];

    seedEnterprises.forEach(e => this.enterprisePathways.set(e.id, e));

    // 5. Seed Primary Demo Persona - Sita
    const sitaProfile: Beneficiary = {
      id: 'ben-sita-001',
      name: 'Sita',
      age: 24,
      gender: 'Female',
      location: 'Chhatrapati Sambhajinagar (Aurangabad Rural)',
      district: 'Aurangabad',
      state: 'Maharashtra',
      pincode: '431006',
      language: 'Marathi',
      education: '10th Class Pass',
      current_occupation: 'Agricultural Laborer',
      previous_occupation: 'Seasonal farming work',
      family_occupation: 'Smallholder Agriculture',
      existing_skills: ['Basic Farming', 'Pumphouse Operations', 'Hand Tools Handling'],
      experience_years: 3,
      desired_occupation: 'Electrical & Solar Work',
      interests: ['Solar Energy', 'Electrical Wiring', 'Appliance Repair'],
      employment_preference: 'wage',
      mobility_km: 15,
      physical_constraints: 'None',
      digital_literacy: 'basic',
      income_category: 'BPL / PM-AJAY Beneficiary Target',
      status: 'analyzed',
      created_at: new Date().toISOString()
    };

    this.beneficiaries.set(sitaProfile.id, sitaProfile);

    // Initial Outcome for Sita
    this.outcomes.set(sitaProfile.id, {
      id: 'out-sita-001',
      beneficiary_id: sitaProfile.id,
      training_status: 'Enrolled',
      completion_date: undefined,
      certification_status: 'Pending',
      employment_status: 'Unemployed',
      enterprise_status: 'None',
      last_updated: new Date().toISOString()
    });

    // Generate 499 additional realistic synthetic beneficiary profiles for demo analytics
    const districts = ['Aurangabad', 'Jalna', 'Nanded', 'Latur', 'Beed', 'Parbhani', 'Osmanabad'];
    const occupations = ['Agriculture', 'Seasonal Construction', 'Household Tailoring', 'Shop Assistant', 'Unemployed Youth', 'Handicraft Weaver'];
    const interestsList = ['Solar & Electrical', 'Garment & Apparel', 'Healthcare Assistant', 'Auto Repair', 'Data Entry & IT', 'Organic Farming'];

    for (let i = 2; i <= 500; i++) {
      const bId = `ben-syn-${i.toString().padStart(3, '0')}`;
      const dist = districts[i % districts.length];
      const occ = occupations[i % occupations.length];
      const int = interestsList[i % interestsList.length];
      const statusList: ('profiled' | 'analyzed' | 'enrolled' | 'placed' | 'self_employed')[] = [
        'profiled', 'analyzed', 'enrolled', 'placed', 'self_employed'
      ];
      const status = statusList[i % statusList.length];

      const ben: Beneficiary = {
        id: bId,
        name: `Beneficiary #${1000 + i}`,
        age: 18 + (i % 27),
        gender: i % 3 === 0 ? 'Female' : 'Male',
        location: `${dist} District Village`,
        district: dist,
        state: 'Maharashtra',
        pincode: `43100${(i % 9) + 1}`,
        language: i % 2 === 0 ? 'Marathi' : 'Hindi',
        education: i % 4 === 0 ? '8th Pass' : (i % 3 === 0 ? '12th Pass' : '10th Pass'),
        current_occupation: occ,
        existing_skills: [occ.toLowerCase() + ' basics', 'manual work'],
        experience_years: 1 + (i % 5),
        desired_occupation: int,
        interests: [int],
        employment_preference: i % 3 === 0 ? 'self_employment' : 'wage',
        mobility_km: 10 + ((i * 5) % 35),
        digital_literacy: i % 2 === 0 ? 'basic' : 'none',
        status: status,
        created_at: new Date(Date.now() - (i * 86400000)).toISOString()
      };
      this.beneficiaries.set(bId, ben);

      // Add outcome
      this.outcomes.set(bId, {
        id: `out-syn-${i.toString().padStart(3, '0')}`,
        beneficiary_id: bId,
        training_status: status === 'placed' || status === 'self_employed' ? 'Completed' : (status === 'enrolled' ? 'Enrolled' : 'Not Started'),
        certification_status: status === 'placed' || status === 'self_employed' ? 'Certified' : 'Pending',
        employment_status: status === 'placed' ? 'Wage Employed' : (status === 'self_employed' ? 'Self Employed' : 'Unemployed'),
        enterprise_status: status === 'self_employed' ? 'Operational' : 'None',
        placement_date: status === 'placed' ? new Date(Date.now() - (i * 40000000)).toISOString() : undefined,
        income_band: status === 'placed' || status === 'self_employed' ? '₹12,000 - ₹18,000 / mo' : undefined,
        last_updated: new Date().toISOString()
      });
    }
  }
}

export const store = new InMemoryStore();
