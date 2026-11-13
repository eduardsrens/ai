import * as THREE from './vendor/three.module.js';
export class PartyWorld {
 constructor(container, types) {
  this.el=container; this.types=types; this.angle=.12; this.zoom=1; this.moving=false;this.time=0;
  this.scene=new THREE.Scene();
  this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.setClearColor(0x000000,0);this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.08;
  container.appendChild(this.renderer.domElement);
  this.camera=new THREE.PerspectiveCamera(42,1,.1,180);
  this.cameraLook=new THREE.Vector3();this.cinematic=false;this.skipShot=false;
  this.hud=document.createElement('div');this.hud.className='cinematic-hud';
  this.hud.innerHTML='<div class="shot-top"><span class="shot-brand">POCKET PARTY <i>IN THE MOMENT</i></span><button class="shot-skip">Back to board <span>Esc</span></button></div><div class="shot-caption"><span class="shot-player"></span><h2></h2><p></p><span class="shot-status">THIRD-PERSON CAMERA · FOLLOWING THE ACTION</span></div>';
  container.append(this.hud);this.hud.querySelector('button').onclick=()=>this.skipShot=true;
  document.addEventListener('keydown',e=>{if(this.cinematic&&e.code==='Escape'){e.preventDefault();this.skipShot=true}});
  this.scene.add(new THREE.AmbientLight(0xfff7df,1.5));const sun=new THREE.DirectionalLight(0xfff6da,2.5);sun.position.set(-15,28,13);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-23,right:23,top:23,bottom:-23,near:1,far:80});sun.shadow.normalBias=.04;sun.shadow.bias=-.0001;sun.shadow.radius=4;this.scene.add(sun);
  const fill=new THREE.DirectionalLight(0xe9f1f2,.8);fill.position.set(15,10,-12);this.scene.add(fill);
  this.world=new THREE.Group();this.scene.add(this.world);this.mats=new Map();this.build();this.makePawns();
  const shadow=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.ShadowMaterial({color:0x45543a,opacity:.13}));shadow.rotation.x=-Math.PI/2;shadow.position.y=-.67;shadow.receiveShadow=true;this.scene.add(shadow);
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);
  let down=false,last=0;container.addEventListener('pointerdown',e=>{if(this.cinematic)return;down=true;last=e.clientX;container.setPointerCapture(e.pointerId)});container.addEventListener('pointermove',e=>{if(down){this.angle+=(e.clientX-last)*.005;last=e.clientX;this.updateCamera()}});container.addEventListener('pointerup',()=>down=false);container.addEventListener('pointercancel',()=>down=false);
  container.addEventListener('wheel',e=>{e.preventDefault();if(this.cinematic)return;this.zoom=THREE.MathUtils.clamp(this.zoom-e.deltaY*.0007,.7,1.65);this.resize()},{passive:false});
  this.resize();this.animate();
 }
 mat(color){if(!this.mats.has(color))this.mats.set(color,new THREE.MeshStandardMaterial({color,roughness:.9,flatShading:true}));return this.mats.get(color)}
 mesh(geo,col,x,y,z,parent=this.world){let m=new THREE.Mesh(geo,this.mat(col));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
 box(x,y,z,w,h,d,c,parent){return this.mesh(new THREE.BoxGeometry(w,h,d),c,x,y,z,parent)}
 roundShape(w,d,r){const s=new THREE.Shape();s.moveTo(-w/2+r,-d/2);s.lineTo(w/2-r,-d/2);s.quadraticCurveTo(w/2,-d/2,w/2,-d/2+r);s.lineTo(w/2,d/2-r);s.quadraticCurveTo(w/2,d/2,w/2-r,d/2);s.lineTo(-w/2+r,d/2);s.quadraticCurveTo(-w/2,d/2,-w/2,d/2-r);s.lineTo(-w/2,-d/2+r);s.quadraticCurveTo(-w/2,-d/2,-w/2+r,-d/2);return s}
 slab(w,d,h,r,col,y){const geo=new THREE.ExtrudeGeometry(this.roundShape(w,d,r),{depth:h,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:.13,bevelThickness:.10,curveSegments:5});geo.rotateX(-Math.PI/2);return this.mesh(geo,col,0,y,0)}
 label(text,x,y,z,size=1,color='#f9f5e4',bg=null,rotation=0){const canvas=document.createElement('canvas');canvas.width=512;canvas.height=128;const c=canvas.getContext('2d');if(bg){c.fillStyle=bg;c.fillRect(0,0,512,128)}c.fillStyle=color;c.font='600 72px sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillText(text,256,68);const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;const m=new THREE.Mesh(new THREE.PlaneGeometry(size*4,size),new THREE.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false}));m.rotation.set(-Math.PI/2,0,rotation);m.position.set(x,y,z);this.world.add(m);return m}
 tree(x,z,s=1,type='pine'){
  const g=new THREE.Group();g.position.set(x,.22,z);g.scale.setScalar(s);this.world.add(g);this.box(0,.4,0,.16,.85,.16,0x8b7756,g);
  if(type==='pine'){this.mesh(new THREE.ConeGeometry(.63,1.4,6),0x6d8a61,0,1.4,0,g);this.mesh(new THREE.ConeGeometry(.8,1.3,6),0x7c9669,0,.92,0,g)}
  else{this.mesh(new THREE.IcosahedronGeometry(.85,0),0x95aa76,0,1.25,0,g);this.mesh(new THREE.IcosahedronGeometry(.62,0),0xb1bf87,.4,1.35,.05,g)}return g;
 }
 house(x,z,s=1,rotation=0,color=0xf0e4c9){const g=new THREE.Group();g.position.set(x,.25,z);g.rotation.y=rotation;g.scale.setScalar(s);this.world.add(g);this.box(0,.65,0,1.4,1.3,1.2,color,g);const roof=new THREE.ConeGeometry(1.2,.85,4);const m=this.mesh(roof,0xb96f56,0,1.62,0,g);m.rotation.y=Math.PI/4;m.scale.z=.9;this.box(.42,1.85,-.2,.2,.65,.23,0xd5b994,g);this.box(0,.4,.607,.32,.8,.04,0x7e927e,g);for(const xx of [-.43,.43]){this.box(xx,.8,.61,.28,.33,.03,0x8cabb0,g);this.box(xx,.8,.635,.025,.33,.02,0xf8edd5,g)}this.box(0,.05,.9,.7,.09,.5,0xdcd2b6,g);return g}
 build(){
  this.slab(25.8,18,.43,3.1,0xc7cfad,-.43);this.slab(25.5,17.7,.17,3,0xadbf8d,.0);
  // A single continuous, winding route: 49 distinct spaces.
  this.path=new THREE.CatmullRomCurve3([[-10,0,5.4],[-5,0,6.4],[1,0,6.4],[7.7,0,5.5],[10.2,0,2.4],[9.5,0,-2.5],[6,0,-5.3],[0,0,-5.6],[-6.6,0,-5],[-10,0,-2],[-8.3,0,1.4],[-4,0,2.6],[1.4,0,2.5],[5.3,0,.8],[4,0,-1.8],[.3,0,-1.9],[-2.7,0,-.6]].map(p=>new THREE.Vector3(...p)),false,'catmullrom',.35);
  this.points=this.path.getSpacedPoints(48);const tileGeo=new THREE.ExtrudeGeometry(this.roundShape(1.03,1.3,.12),{depth:.17,bevelEnabled:true,bevelSegments:1,bevelSize:.045,bevelThickness:.04,curveSegments:3});tileGeo.rotateX(-Math.PI/2);
  const colors={start:0xd68468,life:0xf1e5cb,payday:0x7f9f74,family:0xdb9e85,home:0x8faeb0,trap:0xd68b74,chance:0xe4b65f,retirement:0x6e8b70};
  for(let i=0;i<this.points.length;i++){const p=this.points[i];const t=this.path.getTangentAt(i/48);const tile=this.mesh(tileGeo,colors[this.types[i]],p.x,.26,p.z);tile.rotation.y=Math.atan2(t.x,t.z);const symbols={start:'PORTAL',payday:'◆',family:'+',home:'★',chance:'?',trap:'!' };if(symbols[this.types[i]])this.label(symbols[this.types[i]],p.x,.49,p.z,this.types[i]==='start'||i===48?.23:.35,i===0||this.types[i]!=='life'?'#fff5dc':'#a6aa88',null,0);else this.label(String(i).padStart(2,'0'),p.x,.48,p.z,.12,'#b8b397');}
  for(const index of [7,21,35]){const p=this.points[index],t=this.path.getTangentAt(index/48),x=p.x+t.z*.95,z=p.z-t.x*.95;this.box(x,.52,z,.65,.42,.48,0xb2914c);this.box(x,.77,z,.7,.12,.53,0xe3bc62);for(const offset of [-.21,.21])this.box(x+offset,.54,z,.07,.47,.51,0xf0d587);this.box(x,.61,z+.27,.13,.16,.05,0x71643d);this.label('★',x,1.05,z,.4,'#f6d375');}
  // Hills, village, grove, and a small lake are original procedural assets.
  for(const [x,z,s,c] of [[-5,-7.1,2,0x9aaa7e],[-2.2,-7.6,2.5,0xa0af80],[1.2,-7.5,1.8,0x95a776],[-11.1,-.5,1.25,0x9eae7f]]){const m=this.mesh(new THREE.IcosahedronGeometry(s,1),c,x,.15,z);m.scale.y=.48;}
  const lake=new THREE.Mesh(new THREE.CircleGeometry(2.1,12),this.mat(0x91b6b5));lake.rotation.x=-Math.PI/2;lake.scale.set(1.1,.62,1);lake.position.set(7.1,.285,-1);this.world.add(lake);this.label('~ ~',7.2,.295,-.9,.35,'#bfd5ca');
  this.house(-5.8,-1.3,1.05,-.15);this.house(-3.3,-2.4,.75,.2,0xeee8d0);this.house(-.6,-3.6,.65,-.15);this.house(6,3.5,.65,-.4);this.house(-9,3.3,.65,.3);
  for(const [x,z,s] of [[-10,-4,1],[-9,-5.6,1.2],[-7.8,-6.7,.9],[-6,-6.9,1.1],[-4,-7.5,.9],[3,-6.9,.9],[5,-6.8,1.1],[7.2,-5.7,.8],[10,-5,1.1],[11,-3.9,.9],[11,1.5,.8],[10.8,4,.65],[8,6.8,.7],[-11,2.6,.7],[-8,6.7,.7],[-6,4.4,.65],[-1.8,4.5,.55],[3.6,4.5,.65],[2,-.1,.7],[-7,-2.5,.8]])this.tree(x,z,s);
  for(const [x,z,s] of [[-7.5,-1,1],[-3.5,-3.9,.8],[.6,-3.6,.8],[5.8,-3.2,.8],[8,1.6,.8],[-9.8,0,.7],[-4,4.5,.7],[0,4.4,.65]])this.tree(x,z,s,'round');
  // White picket fences and a modest village square.
  for(let i=0;i<8;i++){this.box(-7.35+i*.38,.58,-2.8,.07,.7,.07,0xf6eed8);if(i<7)this.box(-7.16+i*.38,.65,-2.8,.38,.07,.05,0xf6eed8)}
  this.box(-5.85,.45,.1,1.2,.2,.35,0x9b7855);this.box(-5.85,.7,-.02,1.2,.45,.08,0xb08b60);for(const xx of [-6.25,-5.45])this.box(xx,.3,.1,.08,.5,.25,0x786b51);
  // A lighthouse at the lake.
  this.mesh(new THREE.CylinderGeometry(.28,.45,1.7,8),0xf3ecd8,7.8,1.05,-2.8);this.mesh(new THREE.CylinderGeometry(.31,.34,.3,8),0xcf9270,7.8,1.45,-2.8);this.mesh(new THREE.CylinderGeometry(.39,.39,.38,8),0x8dada9,7.8,2.05,-2.8);this.mesh(new THREE.ConeGeometry(.58,.5,8),0xbe7c5f,7.8,2.48,-2.8);
  // Garden details, shrubs, and flowers; fixed seed keeps the board stable.
  let seed=18;const rand=()=>{seed=(seed*16807)%2147483647;return(seed-1)/2147483646};
  for(let i=0;i<95;i++){const x=rand()*23-11.5,z=rand()*15-7.5;if(this.points.some(p=>Math.hypot(p.x-x,p.z-z)<.9)||Math.hypot(x-7,z+1)<2.2)continue;const size=.1+rand()*.18;this.mesh(new THREE.IcosahedronGeometry(size,0),i%4===0?0xeacb87:0x93a777,x,.25,z);}
  this.label('POCKET PARTY',-.5,.29,.35,.47,'#647f52');this.label('A LITTLE FRIENDLY CHAOS',-.5,.29,1.02,.155,'#7b9165');
  // Flags mark both ends of the journey.
  this.flag(-10.7,4.7,0xd88c6f);this.flag(-3.4,-.85,0xf0d798);

 }
 flag(x,z,color){this.box(x,1.05,z,.045,1.7,.045,0xf3edd7);const m=this.mesh(new THREE.BoxGeometry(.6,.37,.035),color,x+.3,1.67,z);m.rotation.z=-.05}
 makePawns(){
  this.pawns=[];
  const colors=[0xd7795c,0x6b9ba8,0x92a86d,0xb497ba];
  for(let i=0;i<4;i++){
   const root=new THREE.Group(),body=new THREE.Group();root.add(body);root.visible=false;this.world.add(root);
   this.box(0,.7,0,.45,.48,.29,colors[i],body);
   this.mesh(new THREE.IcosahedronGeometry(.27,1),0xf0d4ae,0,1.18,0,body);
   this.box(-.095,1.2,.235,.045,.06,.025,0x3f5144,body);this.box(.095,1.2,.235,.045,.06,.025,0x3f5144,body);
   const hat=this.mesh(new THREE.ConeGeometry(.32,.3,6),colors[i],0,1.48,0,body);hat.rotation.y=.2;
   const limbs=[];
   for(const sign of [-1,1]){
    const leg=new THREE.Group();leg.position.set(sign*.13,.5,0);body.add(leg);this.box(0,-.22,0,.16,.43,.18,0x5a6a58,leg);this.box(0,-.4,.04,.2,.1,.28,0xeee6cf,leg);limbs.push(leg);
    const arm=new THREE.Group();arm.position.set(sign*.3,.9,0);body.add(arm);this.box(0,-.18,0,.14,.35,.16,colors[i],arm);this.mesh(new THREE.SphereGeometry(.09,6,4),0xf0d4ae,0,-.38,0,arm);limbs.push(arm);
   }
   const ring=new THREE.Mesh(new THREE.RingGeometry(.38,.44,24),new THREE.MeshBasicMaterial({color:colors[i],transparent:true,opacity:.75,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.y=.015;root.add(ring);
   const shield=new THREE.Mesh(new THREE.SphereGeometry(.9,16,12),new THREE.MeshStandardMaterial({color:0xa8d7cc,transparent:true,opacity:.22,roughness:.2,depthWrite:false}));shield.position.y=.8;shield.visible=false;root.add(shield);
   root.scale.setScalar(.88);this.pawns.push({root,body,limbs,ring,shield,position:0});
  }
 }
 placePawn(id,progress){const pawn=this.pawns[id];const wrapped=((progress%49)+49)%49;const t=Math.min(wrapped,48)/48,p=this.path.getPointAt(t),dir=this.path.getTangentAt(t);const offsets=[[-.18,-.16],[.18,-.16],[-.18,.16],[.18,.16]];pawn.root.position.set(p.x+offsets[id][0],.49,p.z+offsets[id][1]);pawn.root.rotation.y=Math.atan2(dir.x,dir.z);}
 setState(g){this.lastState=structuredClone(g);this.pawns.forEach((p,i)=>{const state=g.players[i];p.root.visible=!!state;if(state){p.position=state.position;p.shield.visible=state.shield;this.placePawn(i,state.position);p.ring.visible=i===g.current;this.neutralPose(p)}});this.needsRender=true}
 neutralPose(p){p.body.position.set(0,0,0);p.body.rotation.set(0,0,0);p.body.scale.setScalar(1);p.limbs.forEach(l=>l.rotation.set(0,0,0));}
 tween(seconds,fn=()=>{}){return new Promise(resolve=>{this.timeline={start:performance.now(),duration:seconds*1000,fn,resolve}})}
 caption(title,text=''){this.hud.querySelector('h2').textContent=title;this.hud.querySelector('.shot-caption p').textContent=text;}
 async beginShot(g,id,title){
  this.skipShot=false;this.cinematic=true;this.followId=id;this.cameraBlend=0;this.shotEnding=false;
  this.hud.querySelector('.shot-player').textContent=g.players[id].name.toUpperCase()+' · ROUND '+g.round;
  this.hud.style.setProperty('--player-color',g.players[id].color);this.caption(title);
  this.el.classList.add('cinematic');document.body.classList.add('action-playing');this.el.dataset.shot='enter';
  this.scene.background=new THREE.Color(0xe3eadc);this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.resize();
  this.shotEntering=true;const from=this.camera.position.clone(),fromLook=this.cameraLook.clone(),pose=this.followPose();
  await this.tween(.85,t=>{this.camera.position.lerpVectors(from,pose.position,t);this.cameraLook.lerpVectors(fromLook,pose.look,t);this.camera.lookAt(this.cameraLook)});this.shotEntering=false;
 }
 async endShot(g){
  this.setState(g);this.caption('Your move. Your moment.',g.event.text);await this.tween(.65);
  this.shotEnding=true;const from=this.camera.position.clone(),look=this.cameraLook.clone(),to=this.overviewPosition();
  this.el.dataset.shot='return';await this.tween(.8,t=>{this.camera.position.lerpVectors(from,to,t);this.cameraLook.lerpVectors(look,new THREE.Vector3(),t);this.camera.lookAt(this.cameraLook)});
  this.cinematic=false;this.el.classList.remove('cinematic');document.body.classList.remove('action-playing');delete this.el.dataset.shot;
  this.scene.background=null;this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.resize();this.shotEnding=false;
 }
 async moveTo(g){
  const id=g.current,from=this.pawns[id].position,to=g.players[id].position,steps=(to-from+49)%49;
  await this.beginShot(g,id,'Let’s take the scenic route.');
  this.el.dataset.shot='running';this.caption(g.players[id].name+' is on the move.',g.roll+' spaces · A little trouble up ahead.');
  if(steps>0&&steps<=6){await this.tween(Math.max(1.5,steps*.5),(t,raw,elapsed)=>{
   this.placePawn(id,from+steps*raw);const p=this.pawns[id],pace=elapsed*13;
   p.body.position.y=Math.abs(Math.sin(pace))*.14;p.body.rotation.x=.1;
   // Opposite arms and legs swing together around their own pivots.
   p.limbs[0].rotation.x=Math.sin(pace)*.7;p.limbs[2].rotation.x=-Math.sin(pace)*.7;
   p.limbs[1].rotation.x=-Math.sin(pace)*.65;p.limbs[3].rotation.x=Math.sin(pace)*.65;
  })}
  this.setState(g);await this.landing(g,this.types[to]);await this.endShot(g);
 }
 makeProp(kind){
  const group=new THREE.Group();this.world.add(group);
  if(kind==='keys'){
   const ring=this.mesh(new THREE.TorusGeometry(.16,.055,6,12),0xedc463,0,.2,0,group);this.box(0,-.09,0,.07,.4,.07,0xedc463,group);this.box(.08,-.23,0,.16,.07,.07,0xedc463,group);
  }else if(kind==='trophy'){
   this.mesh(new THREE.CylinderGeometry(.23,.12,.3,8),0xeac367,0,.15,0,group);this.box(0,-.12,0,.07,.25,.07,0xc9a04d,group);this.box(0,-.28,0,.36,.1,.27,0x9e834e,group);
   for(const x of [-.23,.23]){const handle=this.mesh(new THREE.TorusGeometry(.12,.035,5,8),0xeac367,x,.16,0,group);handle.scale.y=.9}
  }else if(kind==='rocket'){
   const body=this.mesh(new THREE.CylinderGeometry(.09,.09,.35,8),0xe9e2c7,0,0,0,group);body.rotation.x=Math.PI/2;
   const nose=this.mesh(new THREE.ConeGeometry(.1,.18,8),0xd8785e,0,0,.26,group);nose.rotation.x=Math.PI/2;
   this.mesh(new THREE.ConeGeometry(.08,.28,6),0xefbd62,0,0,-.3,group).rotation.x=-Math.PI/2;
  }else if(kind==='heal'){
   this.box(0,0,0,.15,.52,.12,0x9fc78d,group);this.box(0,0,0,.48,.15,.12,0x9fc78d,group);
  }else{
   this.box(0,0,0,.43,.43,.43,0xe5b55d,group);this.box(0,0,0,.46,.08,.46,0xffefb5,group);this.box(0,0,0,.08,.46,.46,0xffefb5,group);
  }return group;
 }
 disposeProp(prop){prop.traverse(o=>{if(o.isMesh)o.geometry.dispose()});prop.removeFromParent();}
 async burst(origin,color=0xf0c469){
  const group=new THREE.Group();this.world.add(group);group.position.copy(origin);const particles=[];
  for(let i=0;i<14;i++){const a=i/14*Math.PI*2;const m=this.mesh(new THREE.IcosahedronGeometry(.07,0),color,0,0,0,group);particles.push({m,a,s:.6+(i%3)*.25})}
  await this.tween(.65,(t,raw)=>{for(const {m,a,s} of particles){m.position.set(Math.cos(a)*raw*s,Math.sin(raw*Math.PI)*.8+raw*.5,Math.sin(a)*raw*s);m.scale.setScalar(1-raw*.9)}});this.disposeProp(group);
 }
 async pickup(g,kind='keys'){
  const p=this.pawns[g.current],prop=this.makeProp(kind);const forward=new THREE.Vector3(0,0,1).applyQuaternion(p.root.quaternion);
  const base=p.root.position.clone().addScaledVector(forward,.55);base.y=.68;prop.position.copy(base);
  this.el.dataset.shot='pickup';this.caption(kind==='trophy'?'A shiny little victory.':kind==='item'?'Something up your sleeve.':kind==='heal'?'A little pick-me-up.':'Finders keepers.',g.event.text);
  await this.tween(.4,t=>{p.body.rotation.x=t*.55;p.body.position.y=-t*.14;p.limbs[1].rotation.x=-t*1.1;p.limbs[3].rotation.x=-t*1.1;prop.rotation.y=t});
  await this.tween(.7,(t,raw)=>{p.body.rotation.x=(1-t)*.55;p.body.position.y=Math.sin(raw*Math.PI)*.24;p.limbs[1].rotation.x=-1.1-t*1.5;p.limbs[3].rotation.x=-1.1-t*1.5;prop.position.y=.68+t*1.55;prop.rotation.y=t*Math.PI*2;prop.scale.setScalar(1+t*.25)});
  await this.burst(prop.position,kind==='heal'?0x94bb80:0xedc465);this.disposeProp(prop);this.neutralPose(p);
 }
 async landing(g,kind){
  if(kind==='trap'){const p=this.pawns[g.current];this.el.dataset.shot='hit';this.caption('Ouch. That looked personal.',g.event.text);await this.tween(.7,(t,raw)=>{p.body.rotation.z=Math.sin(raw*Math.PI*5)*(1-raw)*.3;p.body.position.y=Math.sin(raw*Math.PI)*.25});this.neutralPose(p);}
  else if(kind==='chance')await this.pickup(g,'item');
  else if(kind==='family')await this.pickup(g,'heal');
  else if(kind==='home'){this.el.dataset.shot='chest';this.caption('Eyes on the prize.',g.pending?.text||g.event.text);const p=this.pawns[g.current];await this.tween(.75,(t,raw)=>{p.limbs[3].rotation.x=-Math.sin(raw*Math.PI)*1.6});this.neutralPose(p);}
  else await this.pickup(g,'keys');
 }
 async playEvent(g,{action,body}){
  if(action==='choice'&&body.option!=='buy'){this.setState(g);return}
  await this.beginShot(g,g.current,action==='choice'?'Something worth showing off.':'A little friendly sabotage.');
  const p=this.pawns[g.current];
  if(action==='choice')await this.pickup(g,'trophy');
  else if(body.item==='shield'){
   this.el.dataset.shot='shield';this.caption('Bubble up.',g.event.text);p.shield.visible=true;await this.tween(.75,(t,raw)=>{p.shield.scale.setScalar(.1+.9*t);p.limbs[1].rotation.x=-Math.sin(raw*Math.PI)*2.4;p.limbs[3].rotation.x=-Math.sin(raw*Math.PI)*2.4});p.shield.scale.setScalar(1);
  }else if(body.item==='swap'){
   this.el.dataset.shot='swap';this.caption('Trading places.',g.event.text);await this.tween(.4,t=>p.body.scale.setScalar(Math.max(.02,1-t)));this.setState(g);await this.tween(.5,t=>p.body.scale.setScalar(Math.max(.02,t)));await this.burst(p.root.position.clone().add(new THREE.Vector3(0,.7,0)),0xb59bc5);
  }else{
   const target=this.pawns[body.target];const direction=target.root.position.clone().sub(p.root.position).setY(0).normalize();p.root.rotation.y=Math.atan2(direction.x,direction.z);
   this.el.dataset.shot='attack';this.caption(body.item==='rocket'?'Special delivery.':'Your keys? Our keys.',g.event.text);
   await this.tween(.45,t=>{p.limbs[3].rotation.x=-t*2.2;p.body.rotation.z=-t*.12});
   const prop=this.makeProp(body.item==='rocket'?'rocket':'keys');const a=(body.item==='rocket'?p:target).root.position.clone().add(new THREE.Vector3(0,1,0));const b=(body.item==='rocket'?target:p).root.position.clone().add(new THREE.Vector3(0,1,0));prop.position.copy(a);prop.lookAt(b);
   await this.tween(.8,(t,raw)=>{prop.position.lerpVectors(a,b,raw);prop.position.y+=Math.sin(raw*Math.PI)*1.5;p.limbs[3].rotation.x=-2.2+raw*1.6});this.disposeProp(prop);
   this.followId=body.target;this.el.dataset.shot='impact';await this.tween(.6,(t,raw)=>{target.body.rotation.z=Math.sin(raw*Math.PI*4)*(1-raw)*.3;target.body.position.y=Math.sin(raw*Math.PI)*.35});
   await this.burst(target.root.position.clone().add(new THREE.Vector3(0,.9,0)),body.item==='rocket'?0xe68b63:0xf0ca6b);this.neutralPose(target);this.followId=g.current;
  }
  await this.endShot(g);
 }
 followPose(){const p=this.pawns[this.followId],forward=new THREE.Vector3(0,0,1).applyQuaternion(p.root.quaternion),side=new THREE.Vector3(forward.z,0,-forward.x);return {look:p.root.position.clone().add(new THREE.Vector3(0,1.05,0)).addScaledVector(forward,.35),position:p.root.position.clone().addScaledVector(forward,-4.6).addScaledVector(side,1.8).add(new THREE.Vector3(0,2.8,0))}}
 overviewPosition(){const aspect=this.el.clientWidth/this.el.clientHeight;const half=(aspect<1?15/aspect:12.6)/this.zoom;const distance=half/Math.tan(THREE.MathUtils.degToRad(this.camera.fov/2));return new THREE.Vector3(Math.sin(this.angle)*32+12,30,Math.cos(this.angle)*32).normalize().multiplyScalar(distance)}
 updateCamera(){if(this.cinematic)return;this.camera.position.copy(this.overviewPosition());this.cameraLook.set(0,0,0);this.camera.lookAt(this.cameraLook);this.needsRender=true}
 resize(){const w=this.el.clientWidth,h=this.el.clientHeight;this.renderer.setSize(w,h);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.updateCamera();this.renderer.render(this.scene,this.camera)}
 rotate(dir){if(this.cinematic)return;this.angle+=dir*.22;this.updateCamera()}
 reset(){if(this.cinematic){this.skipShot=true;return}this.angle=.12;this.zoom=1;this.resize()}
 animate(){
  requestAnimationFrame(()=>this.animate());const now=performance.now(),dt=Math.min((now-(this.lastTime||now))/1000,.1);this.lastTime=now;this.time=now/1000;
  const timeline=this.timeline;if(timeline){const raw=this.skipShot?1:Math.min(1,(now-timeline.start)/timeline.duration);timeline.fn(raw*raw*(3-2*raw),raw,(now-timeline.start)/1000);if(raw>=1){this.timeline=null;timeline.resolve()}this.needsRender=true}
  if(this.cinematic&&!this.shotEnding&&!this.shotEntering){const pose=this.followPose(),lerp=1-Math.exp(-dt*7);this.camera.position.lerp(pose.position,lerp);this.cameraLook.lerp(pose.look,lerp);this.camera.lookAt(this.cameraLook);this.needsRender=true;}
  if(this.needsRender||this.cinematic){this.renderer.render(this.scene,this.camera);this.needsRender=false}
 }
}
