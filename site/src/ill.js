/* Plays the illustrations that site/ill.py renders: one step at a time, while the figure is on screen. */
(function () {
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function setup(fig) {
    var steps = JSON.parse(fig.querySelector('.ill-data').textContent);
    var says = Array.prototype.map.call(fig.querySelectorAll('.ill-text li'), function (li) { return li.innerHTML; });
    var toks = {}, marks = {}, lanes = {};
    fig.querySelectorAll('.tok').forEach(function (g) { toks[g.getAttribute('data-t')] = g; });
    fig.querySelectorAll('.mark').forEach(function (g) { marks[g.getAttribute('data-m')] = g; });
    fig.querySelectorAll('.lane').forEach(function (g) { lanes[g.getAttribute('data-l')] = g; });
    var lines = fig.querySelectorAll('.ln');
    var code = fig.querySelector('.ill-code');
    var say = fig.querySelector('.ill-say');
    var clock = fig.querySelector('.ill-clock');
    var dots = fig.querySelectorAll('.dot');
    var prog = fig.querySelector('.ill-prog i');
    var play = fig.querySelector('.ill-play');
    var cur = 0, timer = null, visible = false, playing = !reduce;

    function show(n) {
      cur = (n + steps.length) % steps.length;
      var s = steps[cur];
      Object.keys(s.t).forEach(function (id) {
        var v = s.t[id], g = toks[id];
        g.style.transform = 'translate(' + v[0] + 'px,' + v[1] + 'px)';
        g.setAttribute('class', 'tok s-' + v[2] + (g.classList.contains('small') ? ' small' : ''));
      });
      Object.keys(marks).forEach(function (id) { marks[id].classList.toggle('on', s.m.indexOf(id) >= 0); });
      Object.keys(lanes).forEach(function (id) { lanes[id].classList.toggle('lit', s.l.indexOf(id) >= 0); });
      lines.forEach(function (ln, i) { ln.classList.toggle('on', s.c.indexOf(i) >= 0); });
      code.classList.toggle('focus', s.c.length > 0);
      var first = s.c.length ? lines[s.c[0]] : null;
      if (first && playing && visible) {
        var pre = first.closest('pre'), box = code;
        var top = first.offsetTop - box.clientHeight / 3;
        if (box.scrollHeight > box.clientHeight) box.scrollTo({ top: Math.max(0, top), behavior: reduce ? 'auto' : 'smooth' });
        if (pre.scrollWidth > pre.clientWidth) pre.scrollLeft = 0;
      }
      say.innerHTML = '<span class="ill-n">' + (cur + 1) + '/' + steps.length + '</span> ' + says[cur];
      clock.hidden = !s.k;
      clock.textContent = s.k;
      dots.forEach(function (d, i) { d.classList.toggle('on', i === cur); d.setAttribute('aria-current', i === cur ? 'step' : 'false'); });
      schedule();
    }

    // Long enough to read the caption; the bar under it shows the time left.
    function hold() {
      var len = says[cur].replace(/<[^>]+>/g, '').length;
      return Math.min(12000, Math.max(3800, 1600 + len * 52)) + (cur === steps.length - 1 ? 1800 : 0);
    }

    function schedule() {
      clearTimeout(timer);
      prog.style.animation = 'none';
      void prog.offsetWidth;
      fig.classList.toggle('playing', playing && visible);
      play.setAttribute('aria-label', playing ? 'Pause' : 'Play');
      if (!playing || !visible) return;
      var ms = hold();
      prog.style.animation = 'ill-prog ' + ms + 'ms linear forwards';
      timer = setTimeout(function () { show(cur + 1); }, ms);
    }

    function manual(n) {
      playing = false;
      say.setAttribute('aria-live', 'polite');
      show(n);
    }

    fig.querySelector('.ill-prev').addEventListener('click', function () { manual(cur - 1); });
    fig.querySelector('.ill-next').addEventListener('click', function () { manual(cur + 1); });
    dots.forEach(function (d, i) { d.addEventListener('click', function () { manual(i); }); });
    play.addEventListener('click', function () {
      playing = !playing;
      if (playing && cur === steps.length - 1) show(0); else schedule();
    });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[entries.length - 1].isIntersecting;
        schedule();
      }, { threshold: 0.35 }).observe(fig);
    }
    fig.classList.add('ready');
    if (reduce) fig.classList.add('still');
    show(0);
  }

  document.querySelectorAll('.ill').forEach(setup);
})();
