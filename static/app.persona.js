/*** static/app.persona.js 人物管理 ***/

document.addEventListener("DOMContentLoaded", () => {
  /*** -------------------- 人物管理 -------------------- ***/
  async function loadPersonas() {
    try {
      const res = await fetch("/personas");
      const data = await res.json();
      const container = document.getElementById("persona-list");
      container.innerHTML = "";
      data.personas.forEach(p => {
        const div = document.createElement("div");
        div.innerHTML = `<label><input type="checkbox" value="${p.name}" ${p.selected ? "checked" : ""}> ${p.name}</label>`;
        container.appendChild(div);
      });
      refreshCurrentPersonas();
    } catch (err) {
      console.error("加载 personas 失败:", err);
    }
  }

  async function updatePersonas() {
    const checkboxes = document.querySelectorAll("#persona-list input[type=checkbox]");
    const selected = Array.from(checkboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value)
      .join(",");
    const formData = new FormData();
    formData.append("selected", selected);
    await fetch("/personas", { method: "POST", body: formData });
    refreshCurrentPersonas();
  }

  async function refreshCurrentPersonas() {
    try {
      const res = await fetch("/personas");
      const data = await res.json();
      const current = data.personas.filter(p => p.selected).map(p => p.name).join(", ") || "无";
      document.getElementById("current-personas-display").textContent = current;
    } catch {}
  }

  document.getElementById("btn-update-personas").addEventListener("click", updatePersonas);

  /*** -------------------- system_rules 动态加载 -------------------- ***/
  fetch("/system_rules")
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById("system_rules");
      select.innerHTML = "";
      data.rules.forEach(rule => {
        const opt = document.createElement("option");
        opt.value = rule;
        opt.textContent = rule;
        select.appendChild(opt);
      });
      if (data.rules.includes("book")) select.value = "book";
    })
    .catch(err => console.error("加载 system_rules 失败:", err));

  loadPersonas();
  refreshCurrentPersonas();
});

/*** -------------------- 开局指令 -------------------- ***/
document.addEventListener("DOMContentLoaded", () => {
    // 获取表单元素
    const chatForm = document.getElementById('chat-form');
    const promptBox = document.getElementById('prompt');
    // 主线故事
    document.getElementById('continue-main-btn').addEventListener('click', function() {
    promptBox.value = "继续推进主线故事";
    chatForm.requestSubmit(); // 直接提交表单
    });
    // 温馨剧情
    document.getElementById('continue-con-btn').addEventListener('click', function() {
    promptBox.value = "参考历史内容续温馨情节";
    chatForm.requestSubmit(); // 直接提交表单
    });
    // 按历史内容续写暧昧情节
    document.getElementById('continue-love-btn').addEventListener('click', function() {
    promptBox.value = "参考历史内容续写暧昧情节";
    chatForm.requestSubmit(); // 直接提交表单
    });
    // 按历史内容续写欲望情节
    document.getElementById('continue-desire-btn').addEventListener('click', function() {
    promptBox.value = "参考历史内容续写性爱情节";
    chatForm.requestSubmit(); // 直接提交表单
    });
    // 安清雪
    document.getElementById('an-qx').addEventListener('click', function() {
    promptBox.value = "冰冷的雨水无情地敲打着瀛洲市的柏油路面，霓虹灯的光晕在积水中化开，显得既绚烂又疏离。\n" +
        "你就这样撑着伞，在街角遇见了她。\n" +
        "丰满的乳房和翘臀，腰肢却细得让人心惊，那几乎是一种非人类的纤细，仿佛造物主最偏心的杰作。谁能拒绝一个绝色萝莉般的诱惑？\n" +
        "安清雪，那个曾经在财经杂志上出现过的名字，此刻却像一只被遗弃的湿漉漉的小猫，蜷缩在冰冷的墙角。她身上那件曾经名贵的连衣裙早已被雨水和污渍弄得不成样子，乌黑的长发紧贴着苍白的脸颊，嘴唇冻得发紫，整个人都在不住地颤抖。\n" +
        "你的脚步停在了她的面前。\n" +
        "她似乎察觉到了阴影，缓缓抬起头。那是一张即使在如此狼狈的情况下，依然美得惊心动魄的脸。她的眼神空洞，但在看清你的瞬间，那死寂的眼眸里猛地爆发出了一丝求生的星光。\n" +
        "她扶着墙，用尽全身力气站了起来，踉跄地向你走近一步，声音沙哑而急切：\n" +
        "“您……等，等一下。”\n" +
        "甜糯糯的萝莉音让人心里一颤。\n" +
        "她深吸一口气，雨水顺着她的下颌滴落，仿佛用尽了一生的勇气，对着你大声喊道：\n" +
        "“只要您给我饭吃，我就跟您走，让我干什么都行！我……我会洗衣做饭，天冷了还能……还能帮您暖床……只要……只要给我口饭吃就行！”\n" +
        "她的话语在雨声中显得那么微弱又那么决绝。她紧紧攥着衣角，用一种混合着恐惧、羞耻和孤注一掷的眼神，死死地盯着你，等待着你的审判。";
    chatForm.requestSubmit(); // 直接提交表单
    });
    // 王佩佩
    document.getElementById('wang-pp').addEventListener('click', function() {
    promptBox.value ="“前辈麻烦让一下，谢谢。”\n" +
        "一个清澈又带着一丝软糯的声音在我身后响起。我闻声本能地侧过身。就是这不经意的一瞥，让我的呼吸瞬间停滞，大脑甚至出现了短暂的空白。\n" +
        "一个女孩站在我身后，她就是新来的实习生，王佩佩。\n" +
        "她的身材好得简直不讲道理，常年瑜伽带来的柔韧与平衡感，甚至有些超出现实。但那一瞬间我脑海里却不受控制地冒出几个词：极致的反差感。\n" +
        "她今天穿了一条贴身的针织连衣裙，这让她的身材曲线暴露无遗。那丰盈饱满的胸部，目测绝不止是寻常的丰满，将柔软的布料撑起一个饱满而富有弹性的弧度，随着她轻微的呼吸微微起伏，散发着致命的吸引力。\n" +
        "然而，视线往下，那腰肢却细得让人心惊。盈盈一握这个词用在她身上都显得保守，那几乎是一种非人类的纤细，仿佛造物主最偏心的杰作。在这极致纤腰的衬托下，再往下的臀部曲线就显得愈发挺翘和圆润，形成了一道近乎夸张却又无比和谐的“S”形，每一步都摇曳生姿。\n" +
        "这根本不是简单的“身材好”，这是行走的人间尤物，是将数字变成了活色生香的现实。\n" +
        "她微微仰头看着我，乌黑的长发如丝绸般披散在背后直达翘臀，衬得那张脸白皙得近乎透明。她的眉眼弯弯，带着天生的笑意，但此刻，那双清澈的眸子里似乎还多了一丝若有若无，看穿了我内心震撼的探寻。\n" +
        "“前辈？”见我直勾勾地盯着她，她并没有表现出任何不悦，反而唇角的笑意更深了些，尾音轻轻上扬，带着点俏皮的意味。\n" +
        "我猛地回过神让开路：抱歉，挡着你了。王佩佩欢迎你。”\n" +
        "“嗯，”她对我报以一个灿烂的微笑，眼眸亮晶晶的，“前辈，以后要多多指教哦。”\n" +
        "她从我身边走过，几乎是擦着我的手臂。那一瞬间，我不仅闻到了一阵清甜的、类似栀子花的香气，甚至能感觉到她身体的热度和连衣裙布料下那柔软又紧致的触感。\n" +
        "我僵在原地，看着她走向自己工位的背影——那随着步伐轻轻摇曳的极致腰臀比，构成了一幅极具诱惑力的画面。\n" +
        "我深吸一口气，努力平复狂跳的心脏。好吧，我收回之前的想法。接下来佩佩的实习期，恐怕不会只是“很有意思”那么简单了。这简直是一场对我定力的终极考验。";
    chatForm.requestSubmit(); // 直接提交表单
    });
});