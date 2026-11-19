/* Notificações animadas no topo das páginas (data-notis='[["ícone","classe","título","detalhe"],...]') */
(function(){
  document.querySelectorAll("[data-notis]").forEach(function(box){
    var N; try{N=JSON.parse(box.getAttribute("data-notis"));}catch(e){return;}
    var reduz=matchMedia("(prefers-reduced-motion: reduce)").matches, i=0;
    function nova(){
      var n=N[i++%N.length], el=document.createElement("div");
      el.className="i-noti";
      el.innerHTML='<span class="i-ok '+n[1]+'">'+n[0]+'</span><div><b>'+n[2]+'</b><small>'+n[3]+'</small></div>';
      box.prepend(el);
      requestAnimationFrame(function(){el.classList.add("on");});
      var t=box.querySelectorAll(".i-noti");
      if(t.length>3){var v=t[t.length-1];v.classList.add("sai");setTimeout(function(){v.remove();},500);}
    }
    nova();nova();nova();
    if(!reduz) setInterval(nova,2800);
  });
})();
/* Seções e cartões aparecem suavemente ao rolar a página */
(function(){
  if(matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
  var alvo=document.querySelectorAll("main .secao, main .secao-compacta, main .sv-card, main .calc-item, main .i-cartao, main .card, main .passo");
  var o=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add("rev-on");o.unobserve(e.target);}});},{threshold:.08});
  alvo.forEach(function(el,k){el.classList.add("rev");el.style.transitionDelay=(el.matches(".sv-card,.calc-item,.i-cartao,.card,.passo")?(k%4)*70:0)+"ms";o.observe(el);});
})();
