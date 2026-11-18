export const roomTypes=['Private room','Entire home/apt','Hotel room','Shared room'];
export const regions=['Central Region','East Region','West Region','North-East Region','North Region'];
export const colors={'Private room':'#ff385c','Entire home/apt':'#00858b','Hotel room':'#7852a9','Shared room':'#f6a15c'};
export const sum=(rows,key)=>rows.reduce((s,r)=>s+(Number.isFinite(r[key])?r[key]:0),0);
export const prices=rows=>rows.filter(r=>r.quote_currency==='SGD'&&r.is_price_sgd_verified===1&&r.listed_price_sgd>0).map(r=>r.listed_price_sgd);
export function quantile(values,p){if(!values.length)return null;const s=[...values].sort((a,b)=>a-b);const i=(s.length-1)*p;const lo=Math.floor(i);return s[lo]+(s[Math.ceil(i)]-s[lo])*(i-lo);}
export function stats(rows){const p=prices(rows);const rated=rows.filter(r=>r.review_scores_rating>=1&&r.review_scores_rating<=5);const nights=sum(rows,'calendar_total_nights');return {total:rows.length,valid:p.length,median:quantile(p,.5),p25:quantile(p,.25),p75:quantile(p,.75),coverage:rows.length?p.length/rows.length:null,available:sum(rows,'calendar_available_nights'),nights,ratio:nights?sum(rows,'calendar_available_nights')/nights:null,rated:rated.length,rating:rated.length?sum(rated,'review_scores_rating')/rated.length:null,medianReviews:quantile(rows.map(r=>r.number_of_reviews).filter(Number.isFinite),.5),reviews:sum(rows,'historical_review_records')};}
export const num=(n,d=0)=>n==null?'—':new Intl.NumberFormat('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}).format(n);
export const pct=n=>n==null?'—':`${num(n*100,2)}%`;
export function group(rows,field){return [...new Set(rows.map(r=>r[field]))].map(name=>({name,rows:rows.filter(r=>r[field]===name)}));}
