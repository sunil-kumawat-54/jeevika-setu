import { Request, Response } from 'express';
import { store } from '../db/store';

function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return Math.round(R * c * 10) / 10;
}

export const getTrainingCentres = (req: Request, res: Response) => {
  const { district, courseId } = req.query;
  let centres = Array.from(store.trainingCentres.values());

  if (district && district !== 'All') {
    centres = centres.filter(c => c.district.toLowerCase().includes((district as string).toLowerCase()));
  }
  if (courseId) {
    centres = centres.filter(c => c.courses.includes(courseId as string));
  }

  res.json({ trainingCentres: centres });
};

export const getNearbyTrainingCentres = (req: Request, res: Response) => {
  const { lat, lng, radiusKm, qualificationId } = req.query;
  const userLat = Number(lat) || 19.8762; // Default Sambhajinagar / Aurangabad
  const userLng = Number(lng) || 75.3235;
  const maxRadius = Number(radiusKm) || 25;

  let centres = Array.from(store.trainingCentres.values());

  if (qualificationId) {
    centres = centres.filter(c => c.courses.includes(qualificationId as string));
  }

  const nearby = centres.map(c => ({
    ...c,
    distance_km: calculateDistance(userLat, userLng, c.lat, c.lng)
  }))
  .filter(c => c.distance_km <= maxRadius)
  .sort((a, b) => a.distance_km - b.distance_km);

  res.json({ nearbyCentres: nearby, radiusKm: maxRadius });
};
