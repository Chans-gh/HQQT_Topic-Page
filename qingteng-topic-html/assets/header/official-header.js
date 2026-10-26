/* Official eui.globalheader.js hqqt branch adaptation 1.2.0; see sources.json. */
(() => {
  'use strict';
  const config = Object.freeze({appId:'wwwhqqt',orgId:'94',pOrgId:'93',type:'hqqt',
    userInfo:'https://api.hqwx.com/phpapi/userInfo',account:'https://user.hqqt.com/v2/'});
  function init() {
    const root=document.getElementById('qt-official-header');
    if(!root||root.dataset.qtInitialized)return;
    root.dataset.qtInitialized='true';
    const $=window.jQuery;
    if(!$){root.dataset.runtime='missing-jquery';return;}
    const $root=$(root),search=root.querySelector('#qt-official-search');
    const searchButton=root.querySelector('.search-block'),userButton=root.querySelector('.user-info');
    const userMenu=root.querySelector('#qt-official-user'),menuButton=root.querySelector('.qt-menu-button');
    let searchTimer;
    const toggleUser=open=>{userMenu.hidden=!open;userButton.setAttribute('aria-expanded',String(open));};
    const toggleNav=open=>{root.dataset.menu=String(open);menuButton.setAttribute('aria-expanded',String(open));};
    function closeSearch(){
      if(!search.open)return;
      search.close();clearTimeout(searchTimer);searchButton.setAttribute('aria-expanded','false');searchButton.focus({preventScroll:true});
    }
    $root.on('click.qtOfficial','.search-block',()=>{
      toggleNav(false);toggleUser(false);
      if(search.open){closeSearch();return;}
      search.showModal();searchButton.setAttribute('aria-expanded','true');
      const frame=search.querySelector('iframe');
      if(!frame.getAttribute('src')){
        root.dataset.search='loading';
        frame.addEventListener('load',()=>{clearTimeout(searchTimer);root.dataset.search='loaded';},{once:true});
        frame.src=frame.dataset.src;
        searchTimer=setTimeout(()=>{root.dataset.search='timeout';},12000);
      }
      search.querySelector('.qt-search-close').focus();
    });
    $root.on('click.qtOfficial','.qt-search-close',closeSearch);
    search.addEventListener('cancel',event=>{event.preventDefault();closeSearch();});
    $root.on('click.qtOfficial','.user-info',()=>{toggleNav(false);toggleUser(userMenu.hidden);});
    $root.on('click.qtOfficial','.qt-menu-button',()=>{toggleUser(false);toggleNav(root.dataset.menu!=='true');});
    $root.on('keydown.qtOfficial',event=>{
      if(event.key==='Escape'){
        if(search.open)closeSearch();
        else if(!userMenu.hidden){toggleUser(false);userButton.focus();}
        else if(root.dataset.menu==='true'){toggleNav(false);menuButton.focus();}
      }
    });
    document.addEventListener('click',event=>{if(!root.contains(event.target)){toggleUser(false);toggleNav(false);}});
    root.addEventListener('focusout',()=>setTimeout(()=>{if(!root.contains(document.activeElement)){toggleUser(false);toggleNav(false);}},0));
    window.addEventListener('resize',()=>{if(innerWidth>1000)toggleNav(false);});
    for(const picture of root.querySelectorAll('.avator img,.user-block-left img')){
      const fallback=picture.src;
      picture.addEventListener('error',()=>{if(picture.src!==fallback)picture.src=fallback;});
    }
    root.dataset.runtime='ready';
    // Cookie access stays with the browser's current origin; no query-string token import or cookie rewriting.
    let passport='';
    try{passport=decodeURIComponent((document.cookie.match(/(?:^|;\s*)passport=([^;]*)/)||[])[1]||'');}catch(_error){}
    if(!passport)return;
    root.dataset.auth='loading';
    $.ajax({url:config.userInfo,data:{_appid:config.appId,org_id:config.orgId,orgId:config.orgId,passport},
      dataType:'jsonp',timeout:10000,
      success(response){
        const user=response&&response.status===1&&Array.isArray(response.data)&&response.data[0];
        if(!user){root.dataset.auth='anonymous';return;}
        const name=String(user.nickName||'环球青藤学员');
        for(const el of root.querySelectorAll('.user-name,.qt-official-nickname')){el.textContent=name;el.title=name;}
        try{
          const avatar=new URL(user.faceUrl);
          if(avatar.protocol==='https:'&&(/(^|\.)hqwx\.com$|(^|\.)hqqt\.com$/.test(avatar.hostname)||avatar.hostname==='oss-hqwx-edu24ol.oss-cn-beijing.aliyuncs.com')){
            for(const img of root.querySelectorAll('.avator img,.user-block-left img'))img.src=avatar.href;
          }
        }catch(_error){}
        root.querySelector('.login-btn-01').hidden=true;userButton.hidden=false;root.dataset.auth='authenticated';
      },
      error(){root.dataset.auth='unavailable';root.querySelector('.login-btn-01').title='账户状态暂未取得，可前往官方学习中心继续';}
    });
  }
  window.QingTengHeader=Object.freeze({init,version:'1.2.0'});
  init();
})();
