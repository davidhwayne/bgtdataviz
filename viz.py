from flask import Flask, request, redirect, url_for, make_response, render_template
import pymysql
import csv
import random

app = Flask(__name__)
app.debug = True

def getqueryresult(stmt):
    #replace db with you database and credentials
    db = pymysql.connect(user='root', db='dataviz')
    cur = db.cursor()
    cur.execute(stmt)
    data=cur.fetchall()
    cur.close()
    return data
    
def occdata():
    return [list(g) for g in getqueryresult('select * from occfams order by occfamname,bgtoccname')]

def famdata():
    occs=occdata()
    fams=[]
    for o in occs:
        if [o[0],o[1]] not in fams:
            fams.append([o[0],o[1]])
    return fams
    
def states():
    return [g[0] for g in getqueryresult('select abbrev from states')]
     
def stateareas():
    return dict(getqueryresult('select abbrev,area from states'))
    
def statepop():
    return dict(getqueryresult('select abbrev,population from states'))
    
def statename(abbrev):
    return dict(getqueryresult('select abbrev,name from states'))[abbrev]
    
def stateids():
    stateid = {'AL':1,'AK':2,'AZ':4,'AR':5,'CA':6,'CO':8,'CT':9,
    'DE':10,'FL':12,'GA':13,'HI':15,'ID':16,'IL':17,'IN':18,'IA':19,
    'KS':20,'KY':21,'LA':22,'ME':23,'MD':24,'MA':25,'MI':26,'MN':27,
    'MS':28,'MO':29,'MT':30,'NE':31,'NV':32,'NH':33,'NJ':34,'NM':35,
    'NY':36,'NC':37,'ND':38,'OH':39,'OK':40,'OR':41,'PA':42,'RI':44,
    'SC':45,'SD':46,'TN':47,'TX':48,'UT':49,'VT':50,'VA':51,'WA':53,
    'WV':54,'WI':55,'WY':56}
    return stateid
        
#####basic scales#####
def realityscale():
    return dict(zip(states(),[1]*50))

def populationscale():
    return dict(getqueryresult('select abbrev,(3786816/306406893)*(population/area) from states'))

#####bgtoccscales#####
def bgtoccscale(bgtocc):    
    return dict(getqueryresult("select a.abbrev,(3130391/c.statetotal)*(b.total/a.area) from states a join stateoccs b on a.abbrev=b.state join bgtoccs c on b.bgtocc=c.bgtocc where b.bgtocc='{bgtocc}'".format(bgtocc=bgtocc)))

def famscale(fam):    
    return dict(getqueryresult("select abbrev,scale from occfamscale where occfam={fam}".format(fam=fam)))
    
def popoccscale(bgtocc):    
    return dict(getqueryresult("select st.abbrev,(sto.total/st.population)*(306000000/b.statetotal) from stateoccs sto join states st on st.abbrev=sto.state join bgtoccs b on sto.bgtocc=b.bgtocc where b.bgtocc='{bgtocc}'".format(bgtocc=bgtocc)))

def popfamscale(fam):    
    return dict(getqueryresult("select abbrev,scale from occfamdensscale where occfam={fam}".format(fam=fam)))

#####funscales#####
def samescale(sizetype):
    typehash={'small':2000,'medium':25000,'large':100000,'huge':300000}
    return dict(getqueryresult('select abbrev,{size}/area from states'.format(size=typehash[sizetype])))
    
def invarea():
    return dict(getqueryresult('select abbrev,100000000/(area*area) from states'))
    
def invpop():
    return dict(getqueryresult("select abbrev,1/((3786816/306406893)*(population/area)) from states where abbrev!='AK'"))
    
def randomscale():
    randos=[]
    for i in range(50):
        randos.append(2*random.random())
    return dict(zip(states(),randos))
    
def scaletest():
    return dict(zip(states(),[1]+[0]*49))
    
def argparse():
    return [request.args.get('scale',''),request.args.get('occ',''),request.args.get('fam',''),request.args.get('by',''),request.args.get('size','')]
    
def scalepicker(stype,occ,fam,by,size):
    if stype=='' or stype=='reality':
        stscale=realityscale()
    elif stype=='occ':
        if by=='area':
            stscale=bgtoccscale(occ)
        elif by=='pop':
            stscale=popoccscale(occ)
    elif stype=='fam':
        if by=='area':
            stscale=famscale(fam)
        elif by=='pop':
            stscale=popfamscale(fam)
    elif stype=='population':
        stscale=populationscale()
    elif stype=='random':
        stscale=randomscale()
    elif stype=='same':
        stscale=samescale(size)
    elif stype=='inversearea':
        stscale=invarea()
    elif stype=='inversepop':
        stscale=invpop()
    elif stype=='test':
        stscale=scaletest()
    return stscale
    
def title(scale,occ,fam):
    if scale=='' or scale=='reality':
        return 'Reality'
    elif scale=='occ':
        return ' '.join([getqueryresult("select bgtoccname from bgtoccs where bgtocc='{occ}'".format(occ=occ))[0][0],'Jobs'])
    elif scale=='fam':
        return ' '.join([getqueryresult("select occfamname from occfams where occfam={fam}".format(fam=fam))[0][0],'Jobs'])
    elif scale=='population':
        return 'Population'
    elif scale=='random':
        return 'Random'
    elif scale=='same':
        return 'Similarity'
    elif scale=='inversearea':
        return 'Inverse Area'
    elif scale=='inversepop':
        return 'Inverse Population'
    elif scale=='test':
        return 'Test'
        
@app.route("/", methods=["GET"])
def index():
    [stype,occ,fam,by,size]=[argparse()[0],argparse()[1],argparse()[2],argparse()[3],argparse()[4]]
    stscale=scalepicker(stype,occ,fam,by,size)
    areas=stateareas()
    diffs=[]
    perdiffs=[]
    allstates=[s for s in stscale]
    lowerstates=[s for s in allstates if s!='HI' and s!='AK']
    for s in lowerstates:
        for t in lowerstates:
            if s==t:
                continue
            diffs.append([s,t,stscale[s]-stscale[t],stscale[s],stscale[t]])
            perdiff=float(stscale[s]*areas[s]-stscale[t]*areas[t])/float(stscale[t]*areas[t])
            if perdiff<.1 and perdiff>0:
                perdiffs.append([s,t,stscale[s]-stscale[t],stscale[s],stscale[t]])
    topper=max(perdiffs, key=lambda x: x[2])
    topdiff=max(diffs, key=lambda x: x[2])
    close1=topper[0]
    close2=topper[1]
    lowd=topdiff[1]
    hid=topdiff[0]
    stid=stateids()
    if by!='pop':
        tot=0
        for l in lowerstates:
            tot+=stscale[t]*areas[t]
        lowfactor=str(round(float(3119459*stscale[lowd])/float(tot),2))
        hifactor=str(round(float(3119459*stscale[hid])/float(tot),2))
        difffactor=str(round(float(stscale[hid]*areas[hid])/float(stscale[lowd]*areas[lowd]),2))
    else:
        pops=statepop()
        tot=0
        for l in lowerstates:
            tot+=stscale[t]*pops[t]
        lowfactor=str(round(float(304413242*stscale[lowd])/float(tot),2))
        hifactor=str(round(float(304413242*stscale[hid])/float(tot),2))
        difffactor=str(round(float(stscale[hid]*areas[hid])/float(stscale[lowd]*areas[lowd]),2))
        
    return render_template('index.html',
        title=title(stype,occ,fam),
        occoptions=occdata(),
        famoptions=famdata(),
        scale=stype,
        occ=occ,
        fam=fam,
        by=by,
        size=size,
        close1=stid[close1],
        close2=stid[close2],
        close1name=statename(close1).title(),
        close2name=statename(close2).title(),
        lowdiff=stid[lowd],
        hidiff=stid[hid],
        lowname=statename(lowd).title(),
        hiname=statename(hid).title(),
        lowfactor=lowfactor,
        hifactor=hifactor,
        difffactor=difffactor)
    
@app.route("/fullmap.do", methods=["GET"])
def fullmapper():
    [stype,occ,fam,by,size]=[argparse()[0],argparse()[1],argparse()[2],argparse()[3],argparse()[4]]
    stscale=scalepicker(stype,occ,fam,by,size)
    return render_template('fullmap.html',stscale=stscale)
      
@app.route("/statemap.do", methods=["GET"])
def statemapper():
    [stype,occ,fam,by,size]=[argparse()[0],argparse()[1],argparse()[2],argparse()[3],argparse()[4]]
    id=request.args.get('id','')
    stscale=scalepicker(stype,occ,fam,by,size)
    return render_template('statemap.html',stscale=stscale,id=id)

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=10080)
