<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generatePageSEO } from "../services/seoService.js";
  const seoData = generatePageSEO("Terms of Service", "FixtureCast terms and conditions of use.", "/terms");
  import { Link } from "svelte-routing";
</script>

<SEOHead data={seoData} />

<div class="page-enter max-w-4xl mx-auto">
  <div class="element-enter stagger-1">
    <Link to="/" class="inline-flex items-center text-cyan-400 hover:text-cyan-300 mb-6">
      <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      Back to Home
    </Link>
  </div>

  <div class="glass-card p-8 element-enter stagger-2">
    <h1 class="text-3xl font-bold text-white mb-2">Terms of Service</h1>
    <p class="text-slate-400 mb-8">Last updated: December 2025</p>

    <div class="prose prose-invert max-w-none space-y-6 text-slate-300">
      <section>
        <h2 class="text-xl font-semibold text-white mb-3">1. Acceptance of Terms</h2>
        <p>
          By accessing and using FixtureCast ("the Service"), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the Service.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">2. Age Restriction</h2>
        <p>
          <strong>You must be 18 years or older to use this Service.</strong> The Service provides football match predictions that may be used in conjunction with gambling activities. By using this Service, you confirm that you are at least 18 years old.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">3. Nature of the Service</h2>
        <p>FixtureCast provides:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li>AI-generated football match predictions using proprietary methods</li>
          <li>Historical match data and statistics</li>
          <li>Team and league information</li>
          <li>Live match scores and events</li>
        </ul>
        <p class="mt-3">
          <strong>Important:</strong> FixtureCast is NOT a gambling operator. We do not:
        </p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li>Accept or process bets</li>
          <li>Handle any gambling transactions</li>
          <li>Pay out winnings or accept losses</li>
          <li>Hold a UK Gambling Commission license</li>
        </ul>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">4. Intellectual Property & Trade Secrets</h2>
        <div class="bg-red-900/30 border border-red-700/50 rounded-lg p-4 mb-4">
          <p class="font-medium text-red-300 mb-2">🔒 Proprietary Technology</p>
          <p>
            FixtureCast's prediction system incorporates <strong>proprietary trade secrets</strong> including AI models, prediction algorithms, and methodologies that represent significant investment and competitive advantage.
          </p>
        </div>
        <p>All content, technology, and intellectual property, including but not limited to:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li>Proprietary prediction models and scoring methods</li>
          <li>Prediction algorithms and methodologies</li>
          <li>Data processing techniques</li>
          <li>Software code, APIs, and system architecture</li>
          <li>User interface design, graphics, and branding</li>
          <li>FixtureCast name, logo, and trademarks</li>
        </ul>
        <p class="mt-3">
          are the exclusive property of FixtureCast and protected by copyright, trademark, patent, trade secret, and other intellectual property laws.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">5. Prohibited Activities</h2>
        <div class="bg-slate-800/50 border border-slate-600 rounded-lg p-4">
          <p class="font-medium text-white mb-2">You expressly agree NOT to:</p>
          <ul class="list-disc pl-6 space-y-1">
            <li>Copy, reproduce, distribute, or republish our predictions</li>
            <li>Reverse engineer, decompile, or disassemble any part of the Service</li>
            <li>Attempt to extract, derive, or recreate our prediction algorithms</li>
            <li>Use automated tools, bots, or scrapers to collect data</li>
            <li>Access our APIs except through authorized interfaces</li>
            <li>Resell, sublicense, or commercially exploit our predictions</li>
            <li>Create derivative works based on our technology</li>
            <li>Circumvent security measures or access restrictions</li>
            <li>Use the Service if you are under 18</li>
          </ul>
          <p class="mt-3 text-amber-300">
            Violation of these terms may result in legal action and claims for damages.
          </p>
        </div>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">6. Disclaimer – No Betting Advice</h2>
        <div class="bg-amber-900/30 border border-amber-700/50 rounded-lg p-4">
          <p class="font-medium text-amber-300 mb-2">⚠️ Important Disclaimer</p>
          <p>
            The predictions and information provided by FixtureCast are for <strong>entertainment and informational purposes only</strong>. They do not constitute:
          </p>
          <ul class="list-disc pl-6 mt-2 space-y-1">
            <li>Financial advice</li>
            <li>Betting advice or tips</li>
            <li>Investment recommendations</li>
            <li>Guaranteed outcomes</li>
          </ul>
          <p class="mt-3">
            Past prediction accuracy does not guarantee future results. You should never rely solely on our predictions when making gambling decisions.
          </p>
        </div>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">7. Responsible Gambling</h2>
        <p>
          If you choose to gamble based on information from this Service, you do so at your own risk. We encourage responsible gambling:
        </p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li>Only gamble what you can afford to lose</li>
          <li>Set limits on your gambling activity</li>
          <li>Never chase losses</li>
          <li>Take regular breaks</li>
        </ul>
        <p class="mt-3">
          If you or someone you know has a gambling problem, please contact:
        </p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li><strong>National Gambling Helpline:</strong> 0808 8020 133 (24/7)</li>
          <li><strong>GamCare:</strong> <a href="https://www.gamcare.org.uk" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">gamcare.org.uk</a></li>
          <li><strong>BeGambleAware:</strong> <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">begambleaware.org</a></li>
        </ul>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">8. Limitation of Liability</h2>
        <p>
          To the fullest extent permitted by law:
        </p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li>We provide the Service "as is" without warranties of any kind</li>
          <li>We are not liable for any losses arising from your use of the Service</li>
          <li>We are not liable for any gambling losses you may incur</li>
          <li>We do not guarantee the accuracy of predictions or data</li>
        </ul>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">9. Data Sources</h2>
        <p>
          Football data may be provided by third-party sources. Team logos and names are trademarks of their respective owners. We are not responsible for the accuracy or timeliness of third-party data.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">10. Termination</h2>
        <p>
          We reserve the right to terminate or restrict access to the Service at any time, for any reason, without notice. This includes blocking IPs or users who violate these terms.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">11. Governing Law</h2>
        <p>
          These Terms are governed by the laws of England and Wales. Any disputes shall be subject to the exclusive jurisdiction of the courts of England and Wales.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">12. Changes to Terms</h2>
        <p>
          We may update these Terms from time to time. Continued use of the Service after changes constitutes acceptance of the new Terms.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">13. Contact</h2>
        <p>
          For questions about these Terms, contact us at <a href="https://x.com/fixturecast" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">@fixturecast</a> on X (Twitter).
        </p>
      </section>
    </div>
  </div>
</div>
