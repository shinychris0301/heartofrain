import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=process.env.HOTR_MODEL_OUTPUT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../Monetization');
await fs.mkdir(out,{recursive:true});
const wb=Workbook.create();
const m=wb.worksheets.add('Monthly Model'),c=wb.worksheets.add('Cohort 90d'),e=wb.worksheets.add('Economy');
const money='$#,##0.00;($#,##0.00);"–"',num='#,##0;(#,##0);"–"',pct='0.0%;(0.0%);"–"',dec='0.000;(0.000);"–"';
function base(s,last,col='C'){
 s.showGridLines=false;s.tabColor='#26394D';s.freezePanes.freezeRows(3);
 s.getRange(`A1:${col}${last}`).format={font:{name:'Arial',size:10,color:'#203044'},rowHeight:25,verticalAlignment:'center'};
 s.getRange(`A1:A${last}`).format.columnWidth=36;s.getRange(`B1:B${last}`).format.columnWidth=19;s.getRange(`C1:C${last}`).format.columnWidth=76;
 s.getRange(`C1:C${last}`).format.wrapText=true;
}
function val(s,cell,value){s.getRange(cell).values=[[value]];}
function form(s,cell,value,cross=false){s.getRange(cell).formulas=[[value]];s.getRange(cell).format.font.color=cross?'#008000':'#000000';}
function header(s,row,labels){s.getRangeByIndexes(row-1,0,1,labels.length).values=[labels];s.getRangeByIndexes(row-1,0,1,labels.length).format={fill:'#26394D',font:{color:'#FFFFFF',bold:true},rowHeight:27};}
function inputs(s,start,rows){
 s.getRange(`A${start}:C${start+rows.length-1}`).values=rows;
 s.getRange(`B${start}:B${start+rows.length-1}`).format={font:{color:'#0000FF'},fill:'#EEF4FA'};
}
function title(s,name,note){val(s,'A1',name);s.getRange('A1').format.font={bold:true,size:16,color:'#203044'};s.getRange('A1').format.rowHeight=32;val(s,'A2',note);s.getRange('A2').format.font={size:10,color:'#596B7B'};}
base(m,37);title(m,'Heart of the Rain | Monthly economics','Illustrative inputs only • USD • Blue = editable; black = formula; green = linked formula');
header(m,4,['Calculated outputs','USD / count','Interpretation']);
const mout=[['Gross IAP spend',null,'Ex-tax player spend before refunds and platform fee'],['Net IAP revenue',null,'Refund-adjusted spend less illustrative platform fee'],['Paid ad impressions',null,'DAU-days × participation × opportunities × fill'],['Net ad revenue',null,'Publisher-net eCPM; no additional IAP fee'],['Total net revenue',null,'Net IAP + net publisher ad revenue'],['Variable service cost',null,'DAU-days × variable cost'],['Paid acquisition spend',null,'Paid installs × CPI'],['Operating contribution',null,'Net revenue − service − fixed content/ops − acquisition'],['Net ARPDAU',null,'Net monthly revenue / DAU-days']];m.getRange('A5:C13').values=mout;
for(const [r,f] of [[5,'=B18*B19*B20'],[6,'=B5*(1-B22)*(1-B21)'],[7,'=B17*B16*B23*B24*B25'],[8,'=B7/1000*B26'],[9,'=B6+B8'],[10,'=B17*B16*B27'],[11,'=B29*B30'],[12,'=B9-B10-B28-B11'],[13,'=IFERROR(B9/(B17*B16),0)']])form(m,'B'+r,f);
m.getRange('B5:B13').setNumberFormat(money);m.getRange('B7').setNumberFormat(num);m.getRange('B13').setNumberFormat('$0.000;($0.000);"–"');m.getRange('A12:C12').format.fill='#E3D8C5';m.getRange('A12:B12').format.font.bold=true;
header(m,15,['Editable assumption','Value','Basis / source']);
inputs(m,16,[['Days in modeled month',30,'Example; match reporting window'],['Average daily active users',10000,'Example, not actual players'],['Monthly active users',50000,'Example; same population/window as payer rate'],['Monthly payer conversion',0.025,'Unique verified payers / MAU; example'],['Monthly spend per payer',25,'USD ex-tax, before refunds/fee; example'],['IAP platform fee',0.15,'Illustrative; verify platform, region and program eligibility'],['IAP refund fraction',0.02,'Simplified fraction of gross spend; example'],['Rewarded-ad participation',0.20,'Share of DAU participating on an average day; example'],['Ad opportunities / participant-day',2,'Example; opportunities before fill'],['Opportunity-to-paid-impression rate',0.90,'Simplified fill/show factor; example'],['Publisher-net eCPM',8,'USD / 1,000 paid impressions; example'],['Service cost / active-user-day',0.002,'USD; variable operating expense example'],['Monthly fixed content / operations',5000,'USD example; excludes acquisition and variable service cost'],['Paid installs this month',10000,'Example; not derived from MAU'],['CPI',3.5,'USD per paid install; example']]);
m.getRange('B16:B18').setNumberFormat(num);m.getRange('B19').setNumberFormat(pct);m.getRange('B20').setNumberFormat(money);m.getRange('B21:B23').setNumberFormat(pct);m.getRange('B24').setNumberFormat('0.0');m.getRange('B25').setNumberFormat(pct);m.getRange('B26').setNumberFormat(money);m.getRange('B27').setNumberFormat('$0.000');m.getRange('B28').setNumberFormat(money);m.getRange('B29').setNumberFormat(num);m.getRange('B30').setNumberFormat(money);
val(m,'A32','Input consistency');form(m,'B32','=IF(AND(B16>0,B17>=0,B18>=B17,B19>=0,B19<=1,B20>=0,B21>=0,B21<=1,B22>=0,B22<=1,B23>=0,B23<=1,B24>=0,B25>=0,B25<=1,B26>=0,B27>=0,B28>=0,B29>=0,B30>=0),"OK","CHECK INPUTS")');val(m,'C32','MAU ≥ average DAU; nonnegative inputs; fractions in [0,1]');
val(m,'A34','Scope');val(m,'C34','Sensitivity model, not accounting profit. No actual financial performance, taxes on income, financing or guaranteed forecast.');m.getRange('A34:C34').format.rowHeight=39;
val(m,'A35','Fee references');val(m,'C35','developer.apple.com/app-store/small-business-program/ | support.google.com/googleplay/android-developer/answer/112622');m.getRange('A35:C35').format.rowHeight=42;
val(m,'A36','Checked');val(m,'C36','2026-10-19. Replace examples with cohort/region/platform data.');
m.dataValidations.add({range:'B16',rule:{type:'whole',operator:'between',formula1:1,formula2:366}});

base(c,116,'J');c.getRange('A1:A116').format.columnWidth=31;c.getRange('B1:B116').format.columnWidth=17;c.getRange('C1:C116').format.columnWidth=33;c.getRange('D1:J116').format.columnWidth=19;
title(c,'Heart of the Rain | 90-day cohort','Day 0–90 inclusive • Retention is illustrative piecewise-linear interpolation, not a fitted forecast');
header(c,4,['Editable assumption','Value','Basis']);c.getRange('E4:G4').values=[['90-day output','Value','Interpretation']];c.getRange('E4:G4').format={fill:'#26394D',font:{color:'#FFFFFF',bold:true}};c.getRange('E1:E19').format.columnWidth=26;c.getRange('G1:G19').format.columnWidth=36;
inputs(c,5,[['Cohort installs',10000,'Example acquired cohort'],['Cohort CPI',3.5,'USD example'],['Gross IAP / active-user-day',0.10,'USD ex-tax before fee/refunds; example'],['Net ads / active-user-day',0.01,'USD publisher-net; example'],['Service cost / active-user-day',0.002,'USD example'],['Platform fee',null,'Linked to Monthly Model'],['Refund fraction',null,'Linked to Monthly Model']]);
form(c,'B10',"='Monthly Model'!B21",true);form(c,'B11',"='Monthly Model'!B22",true);
c.getRange('B5').setNumberFormat(num);c.getRange('B6').setNumberFormat(money);c.getRange('B7:B9').setNumberFormat('$0.000');c.getRange('B10:B11').setNumberFormat(pct);
header(c,13,['Retention anchor','Value','Example exact-day retention']);
inputs(c,14,[['D0',1,'Whole acquired cohort'],['D1',.35,'Example, not a benchmark'],['D7',.15,'Example, not a benchmark'],['D30',.05,'Example, not a benchmark'],['D90',.015,'Example, not a benchmark']]);c.getRange('B14:B18').setNumberFormat(pct);
c.getRange('C5:C18').format.rowHeight=29;
c.getRange('E5:G12').values=[['Net revenue / install',null,'90-day horizon'],['Contribution / install',null,'Before acquisition and fixed ops'],['Net revenue ROAS',null,'Net revenue / acquisition spend'],['After-acquisition contribution',null,'Excludes fixed content/ops'],['Modeled payback day',null,'Contribution covers acquisition'],['Break-even CPI',null,'Before fixed cost / risk reserve'],['Retention check',null,'D0=100%; decreasing anchors'],['Cohort input check',null,'Nonnegative inputs / positive installs']];
for(const [r,f] of [[5,'=IFERROR(H112/B5,0)'],[6,'=IFERROR(I112/B5,0)'],[7,'=IFERROR(H112/(B5*B6),0)'],[8,'=I112-B5*B6'],[9,'=IF(COUNTIF(J22:J112,1)=0,"Not reached",MATCH(1,J22:J112,0)-1)'],[10,'=F6'],[11,'=IF(AND(B14=1,B15>=B16,B16>=B17,B17>=B18,B15<=1,B18>=0),"OK","CHECK INPUTS")'],[12,'=IF(AND(B5>0,B6>=0,B7>=0,B8>=0,B9>=0,B10>=0,B10<=1,B11>=0,B11<=1),"OK","CHECK INPUTS")']])form(c,'F'+r,f);
c.getRange('F5:F6').setNumberFormat(money);c.getRange('F7').setNumberFormat('0.00"x"');c.getRange('F8').setNumberFormat(money);c.getRange('F10').setNumberFormat(money);c.getRange('E6:G6').format.fill='#E3D8C5';c.getRange('G5:G12').format.wrapText=true;
header(c,21,['Day','Retention','Expected active','Net IAP','Net ads','Service cost','Contribution','Cum. net revenue','Cum. contribution','Paid back?']);
const daily=[];
for(let day=0;day<=90;day++){
 const r=day+22;
 daily.push([`=${day}`,`=IF(A${r}<=1,$B$14+($B$15-$B$14)*A${r},IF(A${r}<=7,$B$15+($B$16-$B$15)*(A${r}-1)/6,IF(A${r}<=30,$B$16+($B$17-$B$16)*(A${r}-7)/23,$B$17+($B$18-$B$17)*(A${r}-30)/60)))`,`=$B$5*B${r}`,`=C${r}*$B$7*(1-$B$10)*(1-$B$11)`,`=C${r}*$B$8`,`=C${r}*$B$9`,`=D${r}+E${r}-F${r}`,day===0?`=D${r}+E${r}`:`=H${r-1}+D${r}+E${r}`,day===0?`=G${r}`:`=I${r-1}+G${r}`,`=IF(I${r}>=$B$5*$B$6,1,0)`]);
}
c.getRange('A22:J112').formulas=daily;c.getRange('A22:J112').format.font.color='#000000';c.getRange('B22:B112').setNumberFormat(pct);c.getRange('C22:C112').setNumberFormat('#,##0.0');c.getRange('D22:I112').setNumberFormat(money);c.getRange('A112:J112').format.fill='#E3D8C5';
val(c,'A114','Interpretation');val(c,'C114','90-day horizon is not lifetime value. No extrapolation beyond Day90.');c.getRange('C114:J114').format.rowHeight=30;

base(e,35);title(e,'Heart of the Rain | Economy worksheet','Per 100 attempts • Proposed costs/use rates are examples; first-clear reward comes from current project');
header(e,4,['Calculated output','Coins / count','Interpretation']);
e.getRange('A5:C11').values=[['First-clear wins',null,'Attempts × win rate × first-clear share of wins'],['Total free coin faucets',null,'First-clear rewards + other grants + optional ad coins'],['Tool coin sinks',null,'Attempts × tool purchase uses/attempt × example cost'],['Life-refill coin sinks',null,'Refill count × example cost'],['Continue coin sinks',null,'Attempts × continue rate × example cost'],['Net coins per modeled batch',null,'Free faucets − example sinks; purchases not modeled'],['First clears to afford one tool',null,'Rounded up; first-clear coins only']];
for(const [r,f] of [[5,'=B16*B17*B18'],[6,'=B5*B19+B20+B21'],[7,'=B16*B22*B23'],[8,'=B24*B25'],[9,'=B16*B26*B27'],[10,'=B6-SUM(B7:B9)'],[11,'=IFERROR(ROUNDUP(B23/B19,0),0)']])form(e,'B'+r,f);
e.getRange('B5:B11').setNumberFormat(num);e.getRange('A10:C10').format.fill='#E3D8C5';
header(e,15,['Editable assumption','Value','Status / source']);
inputs(e,16,[['Attempts in batch',100,'Illustrative scenario size'],['Win rate per attempt',.60,'Example; no player data supplied'],['First-clear share of wins',.75,'Example; excludes replay rewards'],['Coins per first clear',50,'CURRENT: App/PreLevel/PreLevelAssets.asset; editable scenario input'],['Other free coin grants',1000,'PROPOSED example per batch; no live reward calendar'],['Rewarded-ad coin grants',0,'PROPOSED; disabled in this example; no ad system implemented'],['Tool purchase uses / attempt',.10,'PROPOSED example; not actual use'],['Coins per purchased tool',300,'PROPOSED example cost; not approved or implemented'],['Life refill count per batch',2,'PROPOSED example; no life regeneration/shop service'],['Coins per life refill',500,'PROPOSED example cost; not approved or implemented'],['Paid continue rate / attempt',.05,'PROPOSED example; no paid-continue mechanic implemented'],['Coins per continue',900,'PROPOSED example cost; not approved or implemented']]);
e.getRange('B16:B27').setNumberFormat(num);for(const r of [17,18,22,26])e.getRange('B'+r).setNumberFormat(pct);
val(e,'A29','Input consistency');form(e,'B29','=IF(AND(B16>0,B17>=0,B17<=1,B18>=0,B18<=1,B19>0,B20>=0,B21>=0,B22>=0,B23>=0,B24>=0,B25>=0,B26>=0,B26<=1,B27>=0),"OK","CHECK INPUTS")');
val(e,'A31','Current starting stock');val(e,'C31','Review defaults: Rocket5 / Bomb5 / Orb3 / Golden2; not production-balanced grants.');
val(e,'A32','Current manual tools');val(e,'C32','Hammer/Axe/Ram/Atlas default3 each; reset-on-load defect must be fixed before commerce.');
val(e,'A33','Design decision');val(e,'C33','50 coins +1 star on first clear. Do not treat example coin costs as approved live balance.');
e.getRange('A31:C33').format.rowHeight=39;

for(const s of [m,e])s.getRange('C5:C33').format.font.size=9;
wb.recalculate();
const verification={};
verification.monthly=m.getRange('A5:C13').values;verification.cohort=c.getRange('E5:G12').values;verification.economy=e.getRange('A5:C11').values;
const baseNet=m.getRange('B12').values[0][0];
if(Math.abs(baseNet-(-13704.75))>.01)throw new Error('Monthly expected value mismatch: '+baseNet);
val(m,'B23',0);const noAd=m.getRange('B8').values[0][0];if(noAd!==0)throw new Error('No-ad scenario failed');val(m,'B23',.20);
val(c,'B6',0);const freePayback=c.getRange('F9').values[0][0];if(freePayback!==0)throw new Error('Zero CPI payback failed');val(c,'B6',3.5);
val(c,'B15',1.1);if(c.getRange('F11').values[0][0]!=='CHECK INPUTS')throw new Error('Retention guard failed');val(c,'B15',.35);
wb.recalculate();
verification.scenario_checks={zero_ad_revenue:noAd,zero_CPI_payback_day:freePayback,invalid_retention_detected:true,restored_monthly_contribution:m.getRange('B12').values[0][0]};
verification.formula_scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#N/A|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:25},maxChars:2500});
verification.inspect=await wb.inspect({kind:'table',range:"'Monthly Model'!A5:C13",include:'values,formulas',tableMaxRows:10,tableMaxCols:3,maxChars:3000});
await fs.writeFile(out+'/Workbook_Verification.json',JSON.stringify(verification,null,2));
for(const [s,name,range] of [[m,'Monthly_Model','A1:C36'],[c,'Cohort_Overview','A1:J26'],[c,'Cohort_Final_Days','A103:J114'],[e,'Economy','A1:C33']]){
 const image=await wb.render({sheetName:s.name,range,scale:1.5,format:'png'});await fs.writeFile(out+'/'+name+'.png',new Uint8Array(await image.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(out+'/Heart_of_the_Rain_Monetization_Model.xlsx');
console.log(JSON.stringify({baseNet,cohort:verification.cohort,scenario_checks:verification.scenario_checks,formula_scan:verification.formula_scan},null,2));
