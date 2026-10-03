"""Generate SYNTHETIC demo data for the IE Asset Dashboard showcase.
Nothing here is derived from real records: names, numbers, coordinates and
network geometry are produced by a seeded random generator inside a generic
bounding box on the Lagos mainland."""
import json, math, random
from pathlib import Path

rng = random.Random(20261003)
OUT = Path(__file__).resolve().parent.parent / 'data'

# Six fictional business units laid out on a simple 3x2 grid (not real BU areas)
BUS = [  # name, slug, center lat, center lng, colour, weight
    ('UPLAND',    'upland',   6.705, 3.255, '#f97316', 0.13),
    ('NORTHGATE', 'northgate', 6.705, 3.355, '#10b981', 0.17),
    ('RIVERSIDE', 'riverside', 6.705, 3.455, '#ef4444', 0.15),
    ('WESTFIELD', 'westfield', 6.615, 3.255, '#f59e0b', 0.17),
    ('CENTRAL',   'central',   6.615, 3.355, '#00d4ff', 0.22),
    ('LAKESIDE',  'lakeside',  6.615, 3.455, '#8b5cf6', 0.16),
]
HALF_LAT, HALF_LNG = 0.045, 0.05
SUBNAMES = ['Alpha','Bravo','Cobalt','Delta','Echo','Falcon','Garnet','Harbor','Indigo',
            'Juniper','Kestrel','Lumen','Meridian','Nova','Onyx','Pioneer','Quartz','Raven']
STREETS = ['Sample Street','Demo Avenue','Example Road','Grid Lane','Placeholder Close',
           'Synthetic Crescent','Test Drive','Mock Way','Prototype Street','Model Avenue']
CATS = lambda pairs: [v for v, w in pairs for _ in range(w)]
def pick(pairs): return rng.choices([p[0] for p in pairs], [p[1] for p in pairs])[0]

def jit(v, s): return v + rng.uniform(-s, s)
def r6(v): return round(v, 6)
def r5(v): return round(v, 5)

def cell_poly(lat0, lat1, lng0, lng1, wob=0.004, n=4):
    pts = []
    for i in range(n): pts.append((lng0 + (lng1-lng0)*i/n, lat0))
    for i in range(n): pts.append((lng1, lat0 + (lat1-lat0)*i/n))
    for i in range(n): pts.append((lng1 - (lng1-lng0)*i/n, lat1))
    for i in range(n): pts.append((lng0, lat1 - (lat1-lat0)*i/n))
    pts = [(r5(jit(x, wob)), r5(jit(y, wob))) for x, y in pts]
    pts.append(pts[0])
    return [[list(p) for p in pts]]

features = []
def feat(geom_type, coords, props): features.append({'type':'Feature','geometry':{'type':geom_type,'coordinates':coords},'properties':props})

# Demo service-area envelope (replaces the state boundary layer)
lat_min, lat_max = 6.615-HALF_LAT-0.01, 6.705+HALF_LAT+0.01
lng_min, lng_max = 3.255-HALF_LNG-0.01, 3.455+HALF_LNG+0.01
feat('MultiPolygon', [cell_poly(lat_min, lat_max, lng_min, lng_max, 0.006, 8)],
     {'name':'Demo Service Area','_layer':'lagos','_color':'#f43f5e'})

# UT boundaries: each BU cell split 2x2 -> 4 undertakings per BU
UTS = {}
for bu, slug, clat, clng, col, w in BUS:
    UTS[bu] = []
    k = 1
    for a in range(2):
        for b in range(2):
            la0 = clat - HALF_LAT + a*HALF_LAT; la1 = la0 + HALF_LAT
            ln0 = clng - HALF_LNG + b*HALF_LNG; ln1 = ln0 + HALF_LNG
            name = f'{bu} UT{k}'
            UTS[bu].append((name, la0, la1, ln0, ln1))
            feat('MultiPolygon', [cell_poly(la0, la1, ln0, ln1, 0.0025, 4)],
                 {'name':name,'_layer':'ut_boundary','_color':'#94a3b8','BU_NAME':bu})
            k += 1

# Bulk supply (TCN-style) points: 3 fictional stations
TCN = []
for i, (la, ln) in enumerate([(6.66, 3.30), (6.66, 3.41), (6.585, 3.36)]):
    la, ln = jit(la, 0.01), jit(ln, 0.01)
    TCN.append((la, ln))
    feat('Point', [r6(ln), r6(la)], {'name':f'GRID STATION {"ABC"[i]}','_layer':'tcn','_color':'#ef4444',
         'ADDRESS':f'Demo Grid Road {i+1}','NUM_FEEDER':str(rng.randint(4,9)),'OP_CAPACITY':f'{rng.choice([60,90,120])}MVA'})

# Injection substations: 3 per BU, fictional names
SUBS = []  # (bu, name, short, lat, lng)
si = 0
for bu, slug, clat, clng, col, w in BUS:
    for j in range(3):
        short = SUBNAMES[si]; si += 1
        la = jit(clat, HALF_LAT*0.6); ln = jit(clng, HALF_LNG*0.6)
        name = f'{short.upper()} SUBSTATION'
        SUBS.append((bu, name, short, la, ln))
        ntx = rng.choice([1,2,2,3]); mva = rng.choice([7.5,15,15,15])
        feat('Point', [r6(ln), r6(la)], {'name':name,'_layer':'iss','_color':'#f59e0b','BU_NAME':bu,
             'CAPACITY':f'{ntx}X{mva:g}MVA','OWNERSHIP':'PUBLIC','ADDRESS':f'{rng.randint(1,80)} {rng.choice(STREETS)}',
             'INJECTION':name,'TOTAL_CAP':f'{ntx*mva:g}','POWER_TX':str(ntx),'VOLT_RATIO':'33/11KV'})
        # 33kV line from nearest grid station
        t = min(TCN, key=lambda p: (p[0]-la)**2+(p[1]-ln)**2)
        mid = (jit((t[0]+la)/2, 0.006), jit((t[1]+ln)/2, 0.006))
        feat('MultiLineString', [[[r5(t[1]),r5(t[0])],[r5(mid[1]),r5(mid[0])],[r5(ln),r5(la)]]],
             {'name':f'33KV {short.upper()} LINE','_layer':'33kv_lines','_color':'#06b6d4','FED_NAME':f'33KV {short.upper()} LINE'})

BU_INFO = {b[0]: b for b in BUS}
# 11kV feeders: random walks out of each substation
FEEDERS = []  # dict
for bu, sname, short, la, ln in SUBS:
    slug = BU_INFO[bu][1]; col = BU_INFO[bu][4]
    for f in range(rng.randint(3,5)):
        tx = rng.randint(1,2)
        route = f'{short} F{f+1}'
        fn = f'11-{short}INJ-T{tx}-{route}'
        ang = rng.uniform(0, 2*math.pi); pts = [(la, ln)]
        for s in range(rng.randint(6,10)):
            ang += rng.uniform(-0.6, 0.6)
            step = rng.uniform(0.002, 0.0045)
            p = (pts[-1][0] + step*math.sin(ang), pts[-1][1] + step*math.cos(ang))
            pts.append(p)
        FEEDERS.append({'bu':bu,'sub':sname,'short':short,'route':route,'fn':fn,'pts':pts,'fv':11})
        feat('MultiLineString', [[[r5(p[1]), r5(p[0])] for p in pts]],
             {'name':route.upper(),'_layer':f'ht_lines_{slug}','_color':col,'_bu':bu,'FED_NAME':route.upper()})
    # one 33kV-fed DT group per substation
    FEEDERS.append({'bu':bu,'sub':sname,'short':short,'route':f'{short} 33F','fn':f'33-{short}INJ-T1-{short} 33F',
                    'pts':[(la,ln),(jit(la,0.01),jit(ln,0.01))],'fv':33})

def ut_for(bu, la, ln):
    for name, la0, la1, ln0, ln1 in UTS[bu]:
        if la0 <= la <= la1 and ln0 <= ln <= ln1: return name
    c = min(UTS[bu], key=lambda u: ((u[1]+u[2])/2-la)**2+((u[3]+u[4])/2-ln)**2)
    return c[0]

N = 2400
ASSETS = []
cust_i = 0
bu_w = [b[5] for b in BUS]
for i in range(N):
    bu = rng.choices([b[0] for b in BUS], bu_w)[0]
    cand = [f for f in FEEDERS if f['bu']==bu]
    f = rng.choices(cand, [1 if c['fv']==33 else 6 for c in cand])[0]
    seg = rng.randrange(len(f['pts'])-1); t = rng.random()
    a, b = f['pts'][seg], f['pts'][seg+1]
    la = jit(a[0]+(b[0]-a[0])*t, 0.0018); ln = jit(a[1]+(b[1]-a[1])*t, 0.0018)
    own = pick([('PUBLIC',66),('PRIVATE',33),('PRIVATE MULTIPLE',1)])
    ms = pick([('METERED',77),('UNMETERED',18),('METERED EST.',5)])
    unm = ms=='UNMETERED'
    cs = pick([('CONNECTED',75),('NOT CONNECTED',25)])
    cos = pick([('COMMISSIONED',80),('NOT COMMISSIONED',20)])
    dtname = f'DT {i+1:04d}'
    cust = ''
    if own != 'PUBLIC':
        cust_i += 1; cust = f'Customer {cust_i:04d}'
    year = rng.choices(range(2015,2027),[3,4,5,6,7,8,9,9,10,10,9,6])[0]
    cd = f'{year}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}'
    rec = {
        'sn': i+1, 'dt': 9900000001+i, 'nom': f"{f['fn']}-{dtname}", 'bu': bu, 'ut': ut_for(bu, la, ln),
        'nut': ut_for(bu, la, ln), 'fv': f['fv'], 'fn': f['fn'],
        'srt': pick([('',30),('Band A',15),('Band B',18),('Band C',20),('Band D',10),('No Band',4),('Band E',3)]),
        'own': own, 'ip': pick([('GROUND',51),('POLE MOUNTED',49)]), 'cust': cust,
        'ap': pick([('CIS',98),('ULTIMA',2)]),
        'at': 'NIL' if unm else pick([('POST-PAID',80),('PRE-PAID',8),('N/A',5),('',7)]),
        'ms': ms, 'mn': '' if unm else f'DEMO-{rng.randint(10000000,99999999)}',
        'mfs': 'NIL' if unm else pick([('FUNCTIONAL',93),('FAULTY',4),('FAULTY METER',2),('NON-FUNCTIONAL',1)]),
        'mt': 'NIL' if unm else pick([('VENDOR A',35),('VENDOR B',34),('VENDOR C',12),('VENDOR D',8),('OTHERS',11)]),
        'cap': int(pick([('50',38),('500',27),('100',9),('200',9),('300',8),('25',5),('1000',2),('750',1),('1500',1)])) if f['fv']==11
               else int(pick([('500',40),('1000',30),('1500',15),('2500',15)])),
        'cs': cs, 'cos': cos,
        'ds': pick([('ACTIVE',75),('INACTIVE',20),('SUSPENDED',3),('OUT OF CIRCUIT',1),('DORMANT',1)]),
        'lat': r6(la), 'lng': r6(ln), 'addr': f'{rng.randint(1,120)} {rng.choice(STREETS)}',
        'cd': cd, 'st': 'OGUN STATE' if (bu=='UPLAND' and la>6.72) else 'LAGOS STATE',
        'fs': pick([('ACTIVE',96),('INACTIVE',2),('',2)]), 'sub': f['sub'],
        'fp': pick([('OVERHEAD',97),('UNDERGROUND',2),('',1)]), 'rl': round(rng.uniform(1.5, 14.0), 4),
    }
    ASSETS.append(rec)
    slug = BU_INFO[bu][1]
    feat('Point', [rec['lng'], rec['lat']], {
        'name': rec['nom'], '_layer': f"{'33' if f['fv']==33 else '11'}kv_dss_{slug}", '_color': BU_INFO[bu][4],
        '_bu': bu, 'BU_NAME': bu, 'UT_NAME': rec['ut'], 'DSS_NAME': dtname, 'FED_NAME': f['route'].upper(),
        'FEEDER_NAME': f['fn'], 'DT_CODE': rec['nom'], 'CAPACITY': str(rec['cap']), 'OWNERSHIP': own,
        'INSTALL_POS': rec['ip'], 'METERING': ms, 'METER_NO': rec['mn'], 'CONNECTION': cs, 'COMMISSION': cos,
        'STATUS': rec['ds'], 'ADDRESS': rec['addr'], 'LAT': str(rec['lat']), 'LONG': str(rec['lng']),
        'CIS_DT': str(rec['dt']), 'STATE': rec['st']})

hdr = ('// SYNTHETIC DEMO DATA - generated by scripts/gen_data.py (seeded random).\n'
       '// Not real assets, customers, meters or locations.\n')
def dump(o): return json.dumps(o, separators=(',',':'))
(OUT/'dashboard_data.js').write_text(hdr + '// Key mapping: sn=S/N, dt=DT Number, nom=Nomenclature, bu=BU, ut=UT, nut=New UT, fv=Feeder Voltage,\n'
    '// fn=Feeder Name, srt=SRT Band, own=Ownership, ip=Installation Position, cust=Customer, ap=Acc Platform,\n'
    '// at=Acc Type, ms=Metering Status, mn=Meter Number, mfs=Meter Func Status, mt=Meter Type, cap=Capacity kVA,\n'
    '// cs=Connection Status, cos=Commissioning Status, ds=Disconnection Status, lat/lng, addr, cd=Creation Date,\n'
    '// st=State, fs=Feeder Status, sub=Substation, fp=Feeder Position, rl=Route Length KM\n'
    'const ASSET_DATA = ' + dump(ASSETS) + ';\n')
(OUT/'ie_network_overview.js').write_text(hdr + f'// {len(features)} synthetic features\nvar OV_NETWORK_DATA=' +
    dump({'type':'FeatureCollection','features':features}) + ';\n')

# Upriser & feeder pillar survey (synthetic, no photos)
ROLES = ['Operations & Maintenance Coordinator (OMC)','Operations & Maintenance Officer (OMO)','Operations & Maintenance Supervisor (OMS)']
OFFICERS = [(f'Field Officer {k:02d}', ROLES[k%3]) for k in range(1,13)]
UF = []
for r in rng.sample([a for a in ASSETS if a['own']=='PUBLIC'], 900):
    fp = rng.random() < 0.92
    tt = rng.choices(range(0,7),[30,14,20,17,6,2,1])[0]
    bd = min(tt, rng.choices([0,1,2,3],[85,10,4,1])[0])
    fo, rp = rng.choice(OFFICERS)
    UF.append({'dt': r['nom'], 'bu': r['bu'], 'ut': r['ut'], 'addr': r['addr'], 'gd': tt-bd, 'bd': bd, 'tt': tt,
               'fp': fp, 'ft': pick([('Wired',68),('Fused',32)]) if fp else 'No',
               'fc': pick([('Good',62),('Poor',23),('Excellent',8),('Critical',7)]) if fp else 'No',
               'vl': pick([('Valid',96),('Invalid',4)]), 'ph': [], 'la': r6(jit(r['lat'],0.0004)), 'ln': r6(jit(r['lng'],0.0004)),
               'fo': fo, 'rp': rp, 'ts': f'{rng.randint(1,6)}/{rng.randint(1,28)}/2026 {rng.randint(8,17)}:{rng.randint(0,59):02d}'})
(OUT/'upriser_feeder_pillar.js').write_text(hdr + f'// {len(UF)} records\nvar UF_DATA=' + dump(UF) + ';\n')

# DT maintenance change log (synthetic), three monthly periods
MCATS = ['New DT','DT to Feeder Change','Change of Nomenclature','Change of Commissioning Status','Change of Connection Status',
         'DT to UT Change','Change of Capacity','Change of Metering Status','Change of Meter Number','Change of Address','Delete DT']
def maint_payload(period, ownership, n):
    recs = []; by_cat = {}; by_bu = {}
    pool = [a for a in ASSETS if (a['own']=='PUBLIC') == (ownership=='Public')]
    for k in range(n):
        a = rng.choice(pool); cat = rng.choices(MCATS,[8,10,14,9,12,5,8,9,7,6,3])[0]
        old = new = None
        if cat=='Change of Capacity': old, new = str(a['cap']), str(rng.choice([100,200,300,500]))
        elif cat=='Change of Nomenclature': old, new = a['nom'] + ' (OLD)', a['nom']
        elif cat=='DT to Feeder Change': old, new = a['fn'], rng.choice([f['fn'] for f in FEEDERS if f['bu']==a['bu']])
        elif cat=='Change of Connection Status': old, new = 'NOT CONNECTED', 'CONNECTED'
        elif cat=='Change of Commissioning Status': old, new = 'NOT COMMISSIONED', 'COMMISSIONED'
        elif cat=='Change of Metering Status': old, new = 'UNMETERED', 'METERED'
        elif cat=='Change of Meter Number': old, new = f'DEMO-{rng.randint(10000000,99999999)}', f'DEMO-{rng.randint(10000000,99999999)}'
        elif cat=='DT to UT Change': old, new = a['ut'], rng.choice(UTS[a['bu']])[0]
        elif cat=='Change of Address': old, new = a['addr'], f'{rng.randint(1,120)} {rng.choice(STREETS)}'
        elif cat=='New DT': new = a['nom']
        elif cat=='Delete DT': old = a['nom']
        recs.append({'id': f'{ownership}_{period}_{k}', 'period': period, 'ownership': ownership, 'changeCategory': cat,
            'sheetName': cat, 'bu': a['bu'], 'ut': a['ut'], 'dtNumber': str(a['dt']), 'dtName': a['nom'],
            'oldValue': old, 'newValue': new, 'feeder': a['fn'], 'capacity': a['cap'], 'meteringStatus': a['ms'],
            'meterNumber': a['mn'] or None, 'connectionStatus': a['cs'], 'commissioningStatus': a['cos'],
            'latitude': a['lat'], 'longitude': a['lng'], 'address': a['addr'], 'remark': 'Synthetic demo change', 'state': a['st']})
        by_cat[cat] = by_cat.get(cat,0)+1; by_bu[a['bu']] = by_bu.get(a['bu'],0)+1
    sheets = sorted(set(r['sheetName'] for r in recs))
    return {'period': period, 'ownership': ownership, 'filename': f'demo_{ownership.lower()}_{period}.xlsx', 'totalRecords': len(recs),
            'records': recs, 'sheetsProcessed': [{'sheet': s, 'category': s, 'count': by_cat[s]} for s in sheets],
            'summary': {'totalRecords': len(recs), 'byCategory': by_cat, 'byBU': by_bu, 'sheetCount': len(sheets)}}
periods = ['2026-06','2026-07','2026-08']
M = {'period': periods[-1], 'private': maint_payload(periods[-1],'Private',rng.randint(70,110)),
     'public': maint_payload(periods[-1],'Public',rng.randint(140,200)), 'archive': {}}
for p in periods[:-1]:
    M['archive'][p] = {'private': maint_payload(p,'Private',rng.randint(60,110)), 'public': maint_payload(p,'Public',rng.randint(120,200))}
(OUT/'sample_maintenance.js').write_text(hdr + 'var SAMPLE_MAINT=' + dump(M) + ';\n')
print('assets', len(ASSETS), 'features', len(features), 'uf', len(UF), 'subs', len(SUBS), 'feeders', len(FEEDERS))
