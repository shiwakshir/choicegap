import * as THREE from '/vendor/three.module.min.js';

// Original procedural character. No portrait, downloaded likeness or restricted avatar asset.
let renderer,scene,camera,head,mouth,eyes=[],active=false,presentation='none',phase='ready',hiddenByParticipant=false;
const area=document.getElementById('avatar-area'),mount=document.getElementById('avatar-canvas');
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let raf=0,last=0;
function shape(parent,color,position,scale,radius=1){
  const material=new THREE.MeshStandardMaterial({color,roughness:.7,metalness:0});
  const mesh=new THREE.Mesh(new THREE.SphereGeometry(radius,32,24),material);
  mesh.position.set(...position);mesh.scale.set(...scale);parent.add(mesh);return mesh;
}
function init(){
  if(renderer)return;
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  const height=mount.clientHeight||300;
  renderer.setSize(mount.clientWidth||600,height);mount.replaceChildren(renderer.domElement);
  scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(32,(mount.clientWidth||600)/height,.1,100);camera.position.set(0,1.5,5.5);camera.lookAt(0,1.35,0);
  scene.add(new THREE.HemisphereLight(0xffffff,0x7e8e79,2.4));const key=new THREE.DirectionalLight(0xfff2e2,3);key.position.set(-2,3,4);scene.add(key);
  const person=new THREE.Group();scene.add(person);
  shape(person,0x244b3f,[0,.25,-.03],[1.1,.65,.48]);
  shape(person,0xbb8063,[0,.95,0],[.22,.45,.23]);
  head=new THREE.Group();head.position.set(0,1.7,0);person.add(head);
  shape(head,0xc38e71,[0,0,0],[.58,.77,.54]);
  shape(head,0xc38e71,[-.58,.02,0],[.12,.19,.1]);shape(head,0xc38e71,[.58,.02,0],[.12,.19,.1]);
  shape(head,0x282520,[0,.48,-.11],[.6,.43,.5]);
  shape(head,0x282520,[-.5,.12,-.14],[.15,.45,.42]);shape(head,0x282520,[.5,.12,-.14],[.15,.45,.42]);
  for(const x of [-.22,.22]){
    const eye=new THREE.Group();eye.position.set(x,.16,.465);head.add(eye);eyes.push(eye);
    shape(eye,0xfff7ea,[0,0,0],[.135,.075,.05]);shape(eye,0x4c5a47,[0,0,.042],[.048,.052,.018]);shape(eye,0x101717,[0,0,.058],[.024,.032,.009]);shape(eye,0xffffff,[-.013,.018,.066],[.009,.009,.005]);
    const brow=shape(head,0x302820,[x,.29,.46],[.15,.023,.024]);brow.rotation.z=x<0?.03:-.03;
  }
  shape(head,0xbc8063,[0,-.005,.52],[.075,.16,.105]);shape(head,0xba7c60,[0,-.09,.565],[.09,.065,.07]);
  mouth=new THREE.Group();mouth.position.set(0,-.3,.47);head.add(mouth);
  shape(mouth,0x452a28,[0,0,0],[.16,.018,.028]);
  shape(mouth,0xa6625a,[0,.021,.006],[.175,.022,.025]);shape(mouth,0xb57868,[0,-.024,.007],[.17,.025,.024]);
  new ResizeObserver(()=>{if(!renderer)return;const w=mount.clientWidth||600,h=mount.clientHeight||300;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(mount);
}
function animate(now){
  if(!active)return;
  const t=now/1000;
  if(!reduced){
    head.rotation.y=.018*Math.sin(t*.6);head.rotation.z=.008*Math.sin(t*.8);
    const blink=(t%5.7)>5.53?1-.95*Math.sin((t%5.7-5.53)/.17*Math.PI):1;
    eyes.forEach(eye=>eye.scale.y=blink);
    mouth.scale.y=phase==='speaking'?1+2.8*Math.abs(Math.sin(t*13))*Math.abs(Math.sin(t*4.1)):1;
  }else mouth.scale.y=1;
  renderer.render(scene,camera);last=now;raf=requestAnimationFrame(animate);
}
function stop(){active=false;cancelAnimationFrame(raf);}
const controller={
  get visible(){return !area.hidden&&!hiddenByParticipant;},
  async configure(type,show){
    presentation=type;area.hidden=!show||type==='none';mount.hidden=hiddenByParticipant;
    if(area.hidden||hiddenByParticipant){stop();return;}
    document.getElementById('avatar-caption').textContent='3D AI character · approximate speaking animation';
    try{init();if(!active){active=true;raf=requestAnimationFrame(animate);}}catch{area.hidden=true;document.getElementById('voice-status').textContent='The character could not load. Voice and text remain available.';}
  },
  state(value){phase=value;},
  hide(){hiddenByParticipant=!hiddenByParticipant;document.getElementById('hide-avatar').textContent=hiddenByParticipant?'Show character':'Hide character';if(hiddenByParticipant){mount.hidden=true;stop();}else{mount.hidden=false;controller.configure(presentation,true);}},
  stop
};
document.getElementById('hide-avatar').onclick=()=>{controller.hide();area.hidden=false;};
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else if(!area.hidden&&!hiddenByParticipant)controller.configure(presentation,true);});
window.addEventListener('pagehide',stop);
window.moderatorAvatar=controller;
window.dispatchEvent(new CustomEvent('moderator-avatar-ready'));
