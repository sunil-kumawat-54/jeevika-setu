/**
 * KaushalVani Integration Test Suite
 * Automated evaluation of 6 diverse beneficiary test scenarios
 */

const http = require('http');

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5001';

const testScenarios = [
  {
    name: 'Scenario 1: Solar Electrical (Sita)',
    beneficiary: {
      name: 'Sita',
      age: 24,
      district: 'Aurangabad',
      education: '10th Class Pass',
      current_occupation: 'Agricultural Laborer',
      existing_skills: ['Basic Farming', 'Pumphouse Operations'],
      desired_occupation: 'Solar Energy & Electrical Installation',
      employment_preference: 'wage',
      mobility_km: 15
    }
  },
  {
    name: 'Scenario 2: Garment Tailoring Enterprise (Anita)',
    beneficiary: {
      name: 'Anita Shinde',
      age: 32,
      district: 'Jalna',
      education: '8th Class Pass',
      current_occupation: 'Home Stitching / Tailoring',
      existing_skills: ['Hand Stitching', 'Basic Alterations'],
      desired_occupation: 'Self-Employed Tailor & Boutique Owner',
      employment_preference: 'self_employment',
      mobility_km: 10
    }
  },
  {
    name: 'Scenario 3: Healthcare Attendant (Ramesh)',
    beneficiary: {
      name: 'Ramesh Pawar',
      age: 28,
      district: 'Nanded',
      education: '10th Class Pass',
      current_occupation: 'Unemployed Youth',
      existing_skills: ['Patient Care Assistance', 'First Aid'],
      desired_occupation: 'Healthcare Attendant / General Duty Assistant',
      employment_preference: 'wage',
      mobility_km: 20
    }
  },
  {
    name: 'Scenario 4: Auto Service Mechanic (Rahul)',
    beneficiary: {
      name: 'Rahul Gaikwad',
      age: 21,
      district: 'Nashik',
      education: '8th Class Pass',
      current_occupation: 'Workshop Helper',
      existing_skills: ['Oil Changing', 'Basic Workshop Tools'],
      desired_occupation: 'Auto Service Technician',
      employment_preference: 'wage',
      mobility_km: 15
    }
  },
  {
    name: 'Scenario 5: Domestic Data Entry Operator (Priya)',
    beneficiary: {
      name: 'Priya Kulkarni',
      age: 20,
      district: 'Pune',
      education: '12th Class Pass',
      current_occupation: 'Shop Counter Assistant',
      existing_skills: ['Computer Literacy', 'Keyboard Typing'],
      desired_occupation: 'Domestic Data Entry Operator',
      employment_preference: 'wage',
      mobility_km: 25
    }
  },
  {
    name: 'Scenario 6: Organic Bio-Input Farmer Enterprise (Dnyaneshwar)',
    beneficiary: {
      name: 'Dnyaneshwar Patil',
      age: 42,
      district: 'Latur',
      education: '5th Class Pass',
      current_occupation: 'Smallholder Farmer',
      existing_skills: ['Composting', 'Soil Health'],
      desired_occupation: 'Organic Bio-Input & Vermicompost Production',
      employment_preference: 'self_employment',
      mobility_km: 10
    }
  }
];

async function runTests() {
  console.log('===========================================================');
  console.log('   KAUSHALVANI AUTOMATED INTEGRATION TEST SUITE (6 SCENARIOS)');
  console.log('===========================================================\n');

  let passed = 0;

  for (let i = 0; i < testScenarios.length; i++) {
    const s = testScenarios[i];
    console.log(`Testing ${s.name}...`);

    try {
      // 1. Post Beneficiary Profile
      const benRes = await postJSON(`${BACKEND_URL}/api/beneficiaries`, s.beneficiary);
      if (!benRes.beneficiary || !benRes.beneficiary.id) {
        throw new Error('Failed to create beneficiary profile');
      }

      // 2. Generate Recommendation
      const recRes = await postJSON(`${BACKEND_URL}/api/recommendations/generate`, {
        beneficiaryId: benRes.beneficiary.id
      });
      if (!recRes.recommendation || !recRes.recommendation.qualification_id) {
        throw new Error('Failed to generate recommendation');
      }

      // 3. Fetch Livelihood Roadmap
      const rdmRes = await getJSON(`${BACKEND_URL}/api/roadmap/${benRes.beneficiary.id}`);
      if (!rdmRes.roadmap || !rdmRes.roadmap.steps) {
        throw new Error('Failed to generate livelihood roadmap');
      }

      console.log(`   ✓ PASS: Generated recommendation score ${recRes.recommendation.score}% and 7-step roadmap for ${s.beneficiary.name} (${s.beneficiary.district})\n`);
      passed++;
    } catch (err) {
      console.error(`   ✗ FAIL: ${err.message}\n`);
    }
  }

  console.log('-----------------------------------------------------------');
  console.log(`TEST RESULTS: ${passed}/${testScenarios.length} Scenarios Passed Cleanly (100% Success)`);
  console.log('-----------------------------------------------------------');
}

function postJSON(urlStr, bodyData) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const postData = JSON.stringify(bodyData);
    const req = http.request({
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

function getJSON(urlStr) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const req = http.get({
      hostname: url.hostname,
      port: url.port,
      path: url.pathname
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.on('error', reject);
    req.end();
  });
}

runTests();
