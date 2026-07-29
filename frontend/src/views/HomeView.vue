<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import TripForm from "../components/TripForm.vue";
import AppFooter from "../components/AppFooter.vue";

const router = useRouter();
const formRef = ref<InstanceType<typeof TripForm> | null>(null);
const heroRef = ref<HTMLElement | null>(null);

// Scenic city images — all from Unsplash, verified accessible
interface CityBlock {
  name: string;
  tag: string;
  image: string;
  side: "left" | "right";
  offsetY: number;
}

const cities: CityBlock[] = [
  {
    name: "北京",
    tag: "Deep Guide",
    image: "https://images.unsplash.com/photo-1608037521277-154cd1b89191?auto=format&fit=crop&w=600&q=80",
    side: "left",
    offsetY: 0,
  },
  {
    name: "大理",
    tag: "Deep Guide",
    image: "https://images.unsplash.com/photo-1528181304800-259b08848526?auto=format&fit=crop&w=600&q=80",
    side: "right",
    offsetY: 50,
  },
  {
    name: "成都",
    tag: "Deep Guide",
    image: "https://tse2-mm.cn.bing.net/th/id/OIP-C.tebmSEfvdj_fXaTVaux0MQHaE7?w=273&h=182&c=7&r=0&o=7&dpr=1.5&pid=1.7&rm=3",
    side: "left",
    offsetY: 30,
  },
  {
    name: "西安",
    tag: "Deep Guide",
    image: "https://images.unsplash.com/photo-1659466248885-8b7a03205661?auto=format&fit=crop&w=600&q=80",
    side: "right",
    offsetY: -10,
  },
  {
    name: "厦门",
    tag: "Deep Guide",
    image: "https://x0.ifengimg.com/ucms/2019_34/9D0ABD0C58570D45FACCD503D0EC932B4B6939E8_w1080_h720.jpg",
    side: "left",
    offsetY: 20,
  },
  {
    name: "三亚",
    tag: "Deep Guide",
    image: "https://tse2-mm.cn.bing.net/th/id/OIP-C.GfqJwQ4yR3bNNXNXF944lgHaFT?w=271&h=194&c=7&r=0&o=7&dpr=1.5&pid=1.7&rm=3",
    side: "right",
    offsetY: 30,
  },
];

const tools = [
  {
    titleEn: "KNOWLEDGE BASE",
    title: "本地攻略检索",
    desc: "覆盖北京、大理、成都、西安、厦门、三亚 6 个热门目的地的深度攻略知识库，为行程生成提供精准参考。",
  },
  {
    titleEn: "MAP NAVIGATION",
    title: "地图导览",
    desc: "基于高德地图的路线可视化与景点标记，虚线箭头指引每日行程路线，地理位置一目了然。",
  },
  {
    titleEn: "WEATHER FORECAST",
    title: "天气感知",
    desc: "自动获取目的地天气预报，根据雨雪或晴天状况智能调整出行建议，做到未雨绸缪。",
  },
  {
    titleEn: "BUDGET TRACKER",
    title: "预算管理",
    desc: "自动拆分交通、住宿、餐饮、门票等各项费用，按天展示每日开销，预算分配清晰可见。",
  },
  {
    titleEn: "EXPORT TOOLS",
    title: "文档导出",
    desc: "支持 Markdown 与 PDF 格式导出，出行前可打印或存入手机，方便随时查阅。",
  },
  {
    titleEn: "AI EDITOR",
    title: "智能调整",
    desc: "用自然语言修改某一天的行程细节，每次调整保留整体结构，无需从头生成。",
  },
];

const quotes = [
  {
    text: "上次去大理，输入偏好后 AI 连我忘了说的想看日落都安排进了行程。到了才发现古城边的咖啡馆真的能看到苍山日落——那种被理解的感觉很奇妙。",
    author: "一位旅行者",
    detail: "2026 年 6 月 · 大理 4 日游",
  },
  {
    text: "成都的行程安排得太对味了。推荐的火锅店就在酒店楼下，第三天上午的自由时间刚好够逛一圈锦里。",
    author: "小周",
    detail: "2026 年 7 月 · 成都 3 日游",
  },
  {
    text: "带着爸妈去三亚，AI 把每天的路程控制在一小时内，还避开了正午的暴晒时段。爸妈玩得轻松，我也省心。",
    author: "林女士",
    detail: "2026 年 5 月 · 三亚 5 日游",
  },
  {
    text: "西安的攻略连洒金桥的肉夹馍要下午三点前去这种细节都写进去了。这份功课比我自己做的还细。",
    author: "Kevin",
    detail: "2026 年 4 月 · 西安 3 日游",
  },
  {
    text: "厦门这个行程用地图一看就明白了——每天的活动范围都不大，带着孩子也不用赶路。最后一天还给了沙滩自由时间。",
    author: "陈先生",
    detail: "2026 年 6 月 · 厦门 4 日游",
  },
  {
    text: "用这个规划了一趟北京四日游，连哪个地铁站离景点最近都标注了。带着父母去，全程没走冤枉路。",
    author: "一只猫",
    detail: "2026 年 3 月 · 北京 4 日游",
  },
  {
    text: "以前做旅行攻略要翻好几个 App，现在一个就够了。唯一的问题是选择太多——每个城市我都想再去一次。",
    author: "阿楠",
    detail: "2026 年 5 月 · 成都 3 日游",
  },
  {
    text: "我让 AI 推荐适合一个人旅行的地方，它给我规划了厦门的行程。五天里有一天完全空白——写着「留给你自己发现」。确实被我发现了很棒的书店。",
    author: "小魚",
    detail: "2026 年 4 月 · 厦门 5 日游",
  },
  {
    text: "最惊喜的是预算功能。之前自己算总是漏这漏那，AI 拆分完才发现原来一趟下来餐饮占比这么大，下次可以在这块省一省。",
    author: "老张",
    detail: "2026 年 6 月 · 西安 3 日游",
  },
  {
    text: "在北京出差顺便多留了两天，让 AI 规划了一个周末行程。它居然知道周五傍晚的景山人最少——这种事只有本地人才会知道。",
    author: "Miles",
    detail: "2026 年 7 月 · 北京 2 日游",
  },
  {
    text: "在三亚度蜜月，AI 推荐了一个游客很少的海滩，傍晚过去几乎包场。老婆说这是整趟旅行最浪漫的傍晚。",
    author: "新郎小刘",
    detail: "2026 年 5 月 · 三亚 5 日游",
  },
  {
    text: "我是做旅游相关行业的，这个产品的 RAG 策略挺有意思。攻略检索+动态规划的双路径设计，在同类项目里算落地得比较完整的。",
    author: "产品经理老王",
    detail: "行业观察 · 2026 年",
  },
  {
    text: "在成都待了三天，每一天的餐饮推荐都恰好在景点附近，不用为了吃饭专门绕路。对于我这种懒得研究路线的人来说太合适了。",
    author: "小杨",
    detail: "2026 年 6 月 · 成都 3 日游",
  },
  {
    text: "导出 PDF 功能救了我一命。出发前打印了一份给爸妈，他们一路上拿着纸质的行程单走得比我还顺。",
    author: "Zoe",
    detail: "2026 年 4 月 · 西安 4 日游",
  },
  {
    text: "大理洱海边的民宿推荐太准了。住进去才发现，AI 选的路线刚好避开了那段在修路的地段，省了至少四十分钟车程。",
    author: "小佳",
    detail: "2026 年 7 月 · 大理 4 日游",
  },
];

const quote = ref(quotes[0]);

onMounted(() => {
  quote.value = quotes[Math.floor(Math.random() * quotes.length)];
});

function pickDest(name: string) {
  formRef.value?.setDestination(name);
  heroRef.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  setTimeout(() => {
    const inp = heroRef.value?.querySelector<HTMLInputElement>('input[placeholder="城市名称"]');
    inp?.focus();
  }, 500);
}
</script>

<template>
  <div class="home">
    <span class="floating-brand" aria-hidden="true">TripCraft</span>
    <span class="floating-signature" aria-hidden="true">— LeonhardJY</span>

    <!-- ============================== -->
    <!--  HERO                          -->
    <!-- ============================== -->
    <section ref="heroRef" class="hero">
      <div class="hero__bg" />

      <div class="section hero__grid">
        <div class="hero__left" v-reveal>
          <p class="hero__eyebrow">TripCraft</p>
          <h1 class="hero__title">
            探索城市<br class="hide-mobile" />最本真的模样
          </h1>
          <p class="hero__subtitle">
            输入目的地与偏好，AI 即刻为你生成完整的旅行方案——<br />
            路线安排、地图导览、预算管理，一步到位。
          </p>
          <div class="hero__tags">
            <span class="hero__tag" @click="pickDest('北京')">北京</span>
            <span class="hero__tag" @click="pickDest('大理')">大理</span>
            <span class="hero__tag" @click="pickDest('成都')">成都</span>
            <span class="hero__tag" @click="pickDest('西安')">西安</span>
            <span class="hero__tag" @click="pickDest('厦门')">厦门</span>
            <span class="hero__tag" @click="pickDest('三亚')">三亚</span>
          </div>
        </div>

        <div class="hero__right" v-reveal>
          <div class="hero__form-heading">
            <span class="hero__form-ornament">✦</span>
            <span>开始规划你的旅程</span>
          </div>
          <div class="hero__form-wrap">
            <TripForm ref="formRef" />
          </div>
        </div>
      </div>
    </section>

    <!-- ============================== -->
    <!--  CITY GALLERY — 3+3            -->
    <!-- ============================== -->
    <section class="section city-section">
      <div class="city-header" v-reveal>
        <p class="eyebrow">Destinations</p>
        <h2>发现目的地之美</h2>
        <p class="text-muted" style="margin-top: var(--spacing-1)">
          精选深度攻略目的地，点击即刻规划
        </p>
      </div>

      <div class="city-gallery">
        <div class="city-gallery__col">
          <button
            v-for="city in cities.filter(c => c.side === 'left')"
            :key="city.name"
            class="city-photo"
            :style="{ marginTop: city.offsetY + 'px' }"
            @click="pickDest(city.name)"
            v-reveal
          >
            <img :src="city.image" :alt="city.name" class="city-photo__img" loading="lazy" />
            <div class="city-photo__overlay" />
            <div class="city-photo__label">
              <span class="city-photo__name">{{ city.name }}</span>
              <span class="city-photo__tag">{{ city.tag }}</span>
            </div>
          </button>
        </div>
        <div class="city-gallery__col city-gallery__col--right">
          <button
            v-for="city in cities.filter(c => c.side === 'right')"
            :key="city.name"
            class="city-photo"
            :style="{ marginTop: city.offsetY + 'px' }"
            @click="pickDest(city.name)"
            v-reveal
          >
            <img :src="city.image" :alt="city.name" class="city-photo__img" loading="lazy" />
            <div class="city-photo__overlay" />
            <div class="city-photo__label">
              <span class="city-photo__name">{{ city.name }}</span>
              <span class="city-photo__tag">{{ city.tag }}</span>
            </div>
          </button>
        </div>
      </div>
    </section>

    <!-- ============================== -->
    <!--  HOW IT WORKS                  -->
    <!-- ============================== -->
    <section class="section how-section" v-reveal>
      <div class="how-header">
        <p class="eyebrow">How It Works</p>
        <h2>三步开启旅程</h2>
      </div>

      <div class="steps">
        <div class="step" v-reveal>
          <div class="step__num">1</div>
          <h3 class="step__title">说出你的想法</h3>
          <p class="step__desc">输入想去的目的地、日期和个人偏好。喜欢什么风格、有什么特殊需求，告诉 us 就好。</p>
        </div>
        <div class="step" v-reveal>
          <div class="step__num">2</div>
          <h3 class="step__title">AI 智能规划</h3>
          <p class="step__desc">大模型配合本地攻略引擎，结合实时地图与天气数据，自动生成完整结构化方案。</p>
        </div>
        <div class="step" v-reveal>
          <div class="step__num">3</div>
          <h3 class="step__title">查看与调整</h3>
          <p class="step__desc">在地图上预览每日路线，用自然语言微调细节，满意后导出或保存，随时查阅。</p>
        </div>
      </div>
    </section>

    <!-- ============================== -->
    <!--  TOOLKIT                       -->
    <!-- ============================== -->
    <section class="section toolkit-section" v-reveal>
      <div class="how-header">
        <p class="eyebrow">Toolkit</p>
        <h2>旅行工具箱</h2>
        <p class="text-muted" style="margin-top: var(--spacing-1)">
          从规划到出行，一站式工具链
        </p>
      </div>

      <div class="toolkit-new">
        <div v-for="t in tools" :key="t.title" class="toolkit-new__card">
          <div class="toolkit-new__marker" />
          <div class="toolkit-new__title">
            {{ t.title }}
            <span class="toolkit-new__title-en">{{ t.titleEn }}</span>
          </div>
          <p class="toolkit-new__desc">{{ t.desc }}</p>
        </div>
      </div>

      <div class="toolkit-stats">
        <div class="toolkit-stat">
          <span class="toolkit-stat__num">6</span>
          <span class="toolkit-stat__label">Deep Guide Cities</span>
        </div>
        <div class="toolkit-stat">
          <span class="toolkit-stat__num">30+</span>
          <span class="toolkit-stat__label">Dynamic Cities</span>
        </div>
        <div class="toolkit-stat">
          <span class="toolkit-stat__num">~20s</span>
          <span class="toolkit-stat__label">Avg. Generation</span>
        </div>
        <div class="toolkit-stat">
          <span class="toolkit-stat__num">3</span>
          <span class="toolkit-stat__label">Data Sources</span>
        </div>
      </div>
    </section>

    <!-- ============================== -->
    <!--  TESTIMONIAL                   -->
    <!-- ============================== -->
    <section class="section quote-section" v-reveal>
      <div class="quote">
        <div class="quote__mark">"</div>
        <blockquote class="quote__text">{{ quote.text }}</blockquote>
        <div class="quote__attribution">
          <div class="quote__avatar">{{ quote.author.charAt(0) }}</div>
          <div>
            <span class="quote__name">{{ quote.author }}</span>
            <span class="quote__detail">{{ quote.detail }}</span>
          </div>
        </div>
      </div>
    </section>

    <AppFooter />
  </div>
</template>

<style scoped>
/* ==============================
   HERO
   ============================== */
.hero {
  position: relative;
  padding: 80px 0 72px;
  overflow: hidden;
  min-height: calc(100vh - var(--header-height));
  display: flex;
  align-items: center;
}

.hero__bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 55% 50% at 20% 5%, rgba(217, 119, 87, 0.07) 0%, transparent 55%),
    radial-gradient(ellipse 40% 40% at 85% 90%, rgba(217, 119, 87, 0.04) 0%, transparent 50%);
  pointer-events: none;
}

.hero__grid {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: 1fr 500px;
  gap: 40px;
  align-items: start;
  width: 100%;
}

.hero__left {
  padding-top: 20px;
}

.hero__eyebrow {
  font-family: var(--font-display);
  font-size: 15px;
  font-style: italic;
  color: var(--color-accent);
  margin-bottom: var(--spacing-3);
}

.hero__title {
  font-size: 54px;
  line-height: 1.08;
  margin-bottom: var(--spacing-4);
  max-width: 520px;
}

.hero__subtitle {
  font-size: 16px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  max-width: 420px;
  margin-bottom: var(--spacing-6);
}

.hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.hero__tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-body);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.hero__tag:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-surface);
}

/* Right side — wider form */
.hero__right {
  position: relative;
}

.hero__form-heading {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.hero__form-ornament {
  color: var(--color-accent);
  font-size: 14px;
}

.hero__form-wrap {
  width: 100%;
}

.hero__form-wrap :deep(.planner) {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--spacing-6);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
}

/* ==============================
   CITY GALLERY
   ============================== */
.city-section {
  padding: var(--spacing-8) var(--spacing-6) var(--spacing-16);
  max-width: 1060px;
}

.city-header {
  margin-bottom: var(--spacing-8);
}

.city-gallery {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

.city-gallery__col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.city-gallery__col--right {
  padding-top: 60px;
}

/* ==============================
   SECTION PADDING
   ============================== */
.how-section,
.toolkit-section {
  padding-top: var(--spacing-16);
  padding-bottom: var(--spacing-16);
}

.quote-section {
  padding-top: var(--spacing-12);
  padding-bottom: var(--spacing-12);
}

.quote {
  max-width: 620px;
  margin: 0 auto;
  text-align: center;
  padding: var(--spacing-8) var(--spacing-6);
  border-top: 1px solid var(--color-divider);
  border-bottom: 1px solid var(--color-divider);
}

.quote__mark {
  font-family: var(--font-display);
  font-size: 48px;
  line-height: 1;
  color: var(--color-accent);
  opacity: 0.35;
  margin-bottom: var(--spacing-3);
}

.quote__text {
  font-family: var(--font-display);
  font-size: 19px;
  line-height: 1.7;
  color: var(--color-text-primary);
  font-style: italic;
  margin: 0 0 var(--spacing-6);
  border: none;
  padding: 0;
}

.quote__attribution {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-3);
}

.quote__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-accent-light);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.quote__name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: left;
}

.quote__detail {
  display: block;
  font-size: 12px;
  color: var(--color-text-secondary);
  text-align: left;
}

/* ==============================
   RESPONSIVE
   ============================== */
@media (max-width: 1024px) {
  .hero__grid {
    grid-template-columns: 1fr;
    gap: 36px;
  }
  .hero {
    min-height: auto;
    padding: 48px 0 40px;
  }
  .hero__title { font-size: 42px; max-width: none; }
  .hero__subtitle { max-width: none; }
  .city-gallery { grid-template-columns: 1fr; }
  .city-gallery__col--right { padding-top: 0; }
  .toolkit-stats { gap: var(--spacing-8); flex-wrap: wrap; }
}

@media (max-width: 640px) {
  .hero { padding: 32px 0 32px; }
  .hero__title { font-size: 34px; }
  .hide-mobile { display: none; }
  .hero__left { padding-top: 0; }
  .hero__grid { grid-template-columns: 1fr; }
  .toolkit-stats { flex-direction: column; align-items: center; gap: var(--spacing-6); }
  .quote__text { font-size: 17px; }
  .city-gallery__col { gap: 16px; }
}
</style>
