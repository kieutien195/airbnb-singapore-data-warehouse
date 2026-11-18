import React from 'react';
import {DataComponent,EvidenceChart,Filters,MetricCard,Section,SortableItem,SortableRegion,useDataApp,useDashboardTabs} from '../../data-app-public.jsx';
import {roomTypes,regions,colors,stats,num,pct,group,prices} from './metrics.js';
import './airbnb.css';
const tabs=[{id:'overview',label:'Overview'},{id:'pricing',label:'Pricing'},{id:'reviews',label:'Availability & Reviews'}];
export function DashboardContent(){
 const {snapshot,queries,filters,setFilter,reviewedRows}=useDataApp();
 const {activeTabId}=useDashboardTabs(tabs);const tab=activeTabId||'overview';
 const rows=reviewedRows('listings');const s=stats(rows);
 const regionRows=group(rows,'neighbourhood_group').map(g=>({Region:g.name,Listings:g.rows.length,availableShare:stats(g.rows).ratio,Reviews:stats(g.rows).reviews}));
 const rooms=roomTypes.map(name=>({name,rows:rows.filter(r=>r.room_type===name)})).filter(g=>g.rows.length);
 const roomRows=rooms.map(g=>({Room:g.name,Listings:g.rows.length,share:g.rows.length/rows.length,rating:stats(g.rows).rating,medianReviews:stats(g.rows).medianReviews}));
 function metric(id,title,value,detail){return <MetricCard id={`${tab}-${id}`} key={id} title={title} queryId="listings" value={value} sourceRows={rows} displayRows={[{metric:title,value,detail}]} periodLabel={detail}/>;}
 function chart(id,title,data,spec,height=270){return <EvidenceChart id={id} title={title} queryId="listings" spec={spec} rows={data} sourceRows={rows} height={height}/>;}
 const cards=tab==='overview'?[
 metric('total','Total listings',num(s.total),'Snapshot 23/09/2026'),metric('median','Median listed price',num(s.median,2),`SGD/night · n=${num(s.valid)}`),metric('share','Private room share',pct(rows.length?rows.filter(r=>r.room_type==='Private room').length/rows.length:null),'Trong nhóm listing đang lọc'),metric('available','Available nights ratio',pct(s.ratio),`${num(s.available)} / ${num(s.nights)} đêm`),metric('rating','Average review score',s.rating==null?'—':`${num(s.rating,2)}/5`,`n=${num(s.rated)} listing có điểm`)
 ]:tab==='pricing'?[
 metric('median','Median listed price',num(s.median,2),'SGD/night'),metric('valid','Valid price listings',num(s.valid),`${num(s.valid)} / ${num(s.total)} listing`),metric('coverage','Valid price coverage',pct(s.coverage),'Giá dương · đã xác minh SGD')
 ]:[metric('available','Available nights ratio',pct(s.ratio),`${num(s.available)} / ${num(s.nights)} đêm`),metric('rating','Average review score',s.rating==null?'—':`${num(s.rating,2)}/5`,`n=${num(s.rated)} listing có điểm`),metric('median-reviews','Median reviews per listing',num(s.medianReviews,1),`n=${num(s.total)} listing`),metric('reviews','Historical review records',num(s.reviews),'04/05/2011–25/09/2026')];
 return <article className="airbnb-page">
 <Filters filters={snapshot.filters} queries={queries} values={filters} onChange={setFilter} trailingControls={<button className="airbnb-reset" onClick={()=>{setFilter('region','all');setFilter('room','all');}}>Đặt lại bộ lọc</button>}/>
 <p className="airbnb-snapshot">Snapshot 23/09/2026 · Singapore</p>
 <SortableRegion id={`airbnb-${tab}-metrics`} variant="freeform" className={`airbnb-metrics count-${cards.length}`}>
 {cards.map(card=><SortableItem key={card.key} id={card.props.id} kind="metric" label={card.props.title}>{card}</SortableItem>)}
 </SortableRegion>
 {!rows.length?<p role="status">Không có listing phù hợp với bộ lọc.</p>:tab==='overview'?<>
 <Section columns={2} spacing="after-metrics">
 {chart('region-room','Listings by region & room type',group(rows,'neighbourhood_group').flatMap(g=>roomTypes.map(room=>({Region:g.name,Room:room,Listings:g.rows.filter(r=>r.room_type===room).length}))),{type:'horizontalStackedBar',x:'Region',y:'Listings',series:'Room',colors})}
 {chart('room-share','Room type distribution',roomRows,{type:'horizontalBar',x:'Room',y:'share',valueDecimals:2})}
 </Section>
 <Section spacing="content">{chart('top-neighbourhoods','Top 10 neighbourhoods by listings',group(rows,'neighbourhood_name').map(g=>({Neighbourhood:g.name,Listings:g.rows.length})).sort((a,b)=>b.Listings-a.Listings||a.Neighbourhood.localeCompare(b.Neighbourhood)).slice(0,10),{type:'horizontalBar',x:'Neighbourhood',y:'Listings'},355)}</Section>
 </>:tab==='pricing'?<>
 <Section spacing="after-metrics"><DataComponent id="price-matrix" queryId="listings" title="Median listed price by region × room type" kind="table" variant="card" sourceRows={rows} displayRows={regions.flatMap(region=>roomTypes.map(room=>{const v=stats(rows.filter(r=>r.neighbourhood_group===region&&r.room_type===room));return {region,room,median:v.median,n:v.valid,p25:v.p25,p75:v.p75};}))}>
 <p className="airbnb-caption">SGD/night · n = listing có giá hợp lệ · rê chuột hoặc chọn ô để xem P25–P75</p>
 <div className="airbnb-table-scroll"><table className="airbnb-matrix"><thead><tr><th>Region</th>{roomTypes.map(r=><th key={r}>{r}</th>)}<th>Total</th></tr></thead><tbody>
 {regions.filter(region=>rows.some(r=>r.neighbourhood_group===region)).map(region=><tr key={region}><th>{region}</th>{roomTypes.map(room=><PriceCell key={room} rows={rows.filter(r=>r.neighbourhood_group===region&&r.room_type===room)}/>)}<PriceCell rows={rows.filter(r=>r.neighbourhood_group===region)}/></tr>)}
 <tr><th>Total</th>{roomTypes.map(room=><PriceCell key={room} rows={rows.filter(r=>r.room_type===room)}/>)}<PriceCell rows={rows}/></tr>
 </tbody></table></div></DataComponent></Section>
 <Section columns={2} spacing="content">
 <DataComponent id="price-ranges" queryId="listings" title="Listed price P25–P75 by room type" kind="custom" variant="card" sourceRows={rows} displayRows={rooms.map(g=>({Room:g.name,...stats(g.rows)}))}><RangePlot groups={rooms}/></DataComponent>
 {chart('price-distribution','Listings by price band',[{label:'≤100',lo:0,hi:100},{label:'>100–200',lo:100,hi:200},{label:'>200–300',lo:200,hi:300},{label:'>300–500',lo:300,hi:500},{label:'>500–1.000',lo:500,hi:1000},{label:'>1.000',lo:1000,hi:Infinity}].map(b=>({Band:b.label,Listings:prices(rows).filter(p=>p>b.lo&&p<=b.hi).length})),{type:'bar',x:'Band',y:'Listings'})}
 </Section>
 </>:<>
 <Section columns={2} spacing="after-metrics">
 {chart('availability-regions','Available nights ratio by region',regionRows,{type:'horizontalBar',x:'Region',y:'availableShare',valueDecimals:2})}
 <DataComponent id="rating-rooms" queryId="listings" title="Average review score by room type" kind="custom" variant="card" sourceRows={rows} displayRows={rooms.map(g=>({Room:g.name,...stats(g.rows)}))}><RatingPlot groups={rooms} overall={s.rating}/></DataComponent>
 </Section>
 <Section columns={2} spacing="content">
 {chart('median-reviews','Median reviews per listing by room type',roomRows,{type:'horizontalBar',x:'Room',y:'medianReviews',valueDecimals:1})}
 {chart('reviews-region','Historical review records by region',regionRows,{type:'horizontalBar',x:'Region',y:'Reviews'})}
 </Section><p className="airbnb-caption">Calendar 25/09/2026–25/09/2027 · Reviews 04/05/2011–25/09/2026. Available nights đo trạng thái mở lịch. Điểm đánh giá tính trên listing có điểm từ 1 đến 5.</p>
 </>}
 </article>;
}
function PriceCell({rows}){const s=stats(rows);const label=s.valid?`Median ${num(s.median,2)} SGD · n=${num(s.valid)} · P25 ${num(s.p25,2)} · P75 ${num(s.p75,2)}`:'Không có giá hợp lệ';return <td style={{background:s.valid?`rgba(0,133,139,${.07+Math.min(s.median/500,1)*.5})`:'#f0f3f5'}}><button title={label} aria-label={label} className="airbnb-cell"><span>{num(s.median,2)}</span>{s.valid>0&&<small>n={num(s.valid)}</small>}<span className="airbnb-tooltip" role="tooltip">{label}</span></button></td>;}
function RangePlot({groups}){const points=groups.map(g=>({...g,...stats(g.rows)})).filter(g=>g.valid);const max=Math.max(100,...points.map(g=>g.p75))*1.1;return <div className="airbnb-range"><p className="airbnb-caption">Đoạn P25–P75 · chấm = trung vị · SGD/night</p>{points.map(g=><div className="airbnb-range-row" key={g.name}><span>{g.name}</span><div className="airbnb-track"><button className="airbnb-interval" style={{left:`${g.p25/max*100}%`,width:`${Math.max(.4,(g.p75-g.p25)/max*100)}%`,background:colors[g.name]}} title={`P25 ${num(g.p25,2)} · Median ${num(g.median,2)} · P75 ${num(g.p75,2)} · n=${g.valid}`} aria-label={`${g.name} P25 ${num(g.p25,2)}, median ${num(g.median,2)}, P75 ${num(g.p75,2)}, n ${g.valid}`}><i style={{left:`${g.p75===g.p25?50:(g.median-g.p25)/(g.p75-g.p25)*100}%`}}/></button></div><b>{num(g.median,2)}</b></div>)}<div className="airbnb-range-axis"><span>0</span><span>{num(max/2,0)}</span><span>{num(max,0)}</span></div></div>;}
function RatingPlot({groups,overall}){return <div className="airbnb-range"><p className="airbnb-caption">n = listing có điểm hợp lệ · mốc nhóm đang lọc {num(overall,2)}/5</p>{groups.map(g=>{const s=stats(g.rows);return <div className="airbnb-range-row" key={g.name}><span>{g.name}</span><div className="airbnb-track airbnb-rating-track"><i className="airbnb-benchmark" style={{left:`${(overall-1)/4*100}%`}}/>{s.rating!=null&&<button className="airbnb-dot" style={{left:`${(s.rating-1)/4*100}%`,background:colors[g.name]}} title={`${num(s.rating,2)}/5 · n=${s.rated}`} aria-label={`${g.name} ${num(s.rating,2)} trên 5, n ${s.rated}`}/>}</div><b>{num(s.rating,2)}<small>n={num(s.rated)}</small></b></div>})}<div className="airbnb-range-axis"><span>1</span><span>3</span><span>5</span></div></div>;}
