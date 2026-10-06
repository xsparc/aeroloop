export function gainParameters(t:number,armed=true):[number,number,number]{
  const u=armed?Math.max(0,Math.min(1,t-34)):0,b=u*u*u*(10+u*(-15+6*u));
  return [b,2.5+1.5*b,2.8+.8*b];
}
export function validateGains(v:unknown,t:number,armed:boolean){
  const expected=gainParameters(t,armed);
  if(!Array.isArray(v)||v.length!==3||!v.every((n,i)=>typeof n==='number'&&Number.isFinite(n)&&Math.abs(n-expected[i])<=1e-12))throw Error('Invalid approach gains');
}
