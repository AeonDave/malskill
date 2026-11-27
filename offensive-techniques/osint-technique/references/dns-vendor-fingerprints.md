# DNS and network vendor fingerprints

Load to name the mail, DNS, CDN, cloud, identity and SaaS vendors behind a domain from its DNS records and the networks of its addresses, or when a host sits behind an edge network.

## Record kinds

Each line below is `vendor [group]: kind=value; ...`. Several values of one kind are separated by commas.

- `mx`, `ns`: a mail exchanger or name server contains the value.
- `spf`: the SPF record (`TXT` starting `v=spf1`) includes a host that contains the value.
- `cname`: a well-known name (`autodiscover`, `status`, `help`, a DKIM selector) points to a host that contains the value.
- `txt`: a `TXT` record contains the value, a verification token added once for the vendor (`^` anchors the start).
- `rua`: the DMARC report address (`rua=` in the `_dmarc` TXT record) is at a host that contains the value.
- `dkim`: a selector of exactly that name exists (`<selector>._domainkey.<domain>`).
- `asn`: the number of a network the vendor runs.
- A trailing `$` means the host name must end with the value.

## Reading a match

- `mx`, `ns`, `spf`, `cname`, `rua`, `dkim`: the vendor carries that service now.
- `txt` only proves the organization verified its domain with the vendor at some point; it may be years old.
- `asn` says where a host lives, not whose it is: a customer's server in a cloud network is still the customer's.
- Keep values specific; a short common word matches unrelated hosts. An unmatched record is "unrecognised", not a guess.
- Spot-checked on 2026-11-27 against the live records of Google, Microsoft, Cloudflare and AWS domains. Vendors rename hosts, so a miss means unrecognised, not absent.

## Edge-fronted hosts

- Detect with several signals: a `CNAME` into the vendor, an address in its ASN, the vendor `cpes` entry and the `cdn` tag in Shodan InternetDB (`https://internetdb.shodan.io/<ip>`). The tag is a positive hint only: on 2026-11-27 `104.16.132.229` carried `cdn` and `1.1.1.1`, also Cloudflare, did not.
- A cloud provider's ASN also hosts ordinary servers; use the provider's published address ranges when the distinction matters.
- An edge address says nothing about who owns the origin or where it is. Record "served through <vendor>".
- Passive origin candidates: older DNS answers from before the edge was added (passive DNS), subdomains from CT that resolve outside the vendor's ranges, and certificate names seen on addresses outside the edge. `MX` and SPF hosts are mail hosts, not the web origin. Report each as a candidate with evidence and confidence.
- Confirming a candidate means sending it a request that names the protected site: that is active recon (see [active-recon.md](../../recon-technique/references/active-recon.md)).

## mail — Mailbox and mail filtering
- Microsoft 365 [Microsoft]: mx=mail.protection.outlook.com; spf=spf.protection.outlook.com; cname=autodiscover.outlook.com; txt=^ms=ms
- Google Workspace [Google]: mx=aspmx.l.google.com, googlemail.com, smtp.google.com; spf=_spf.google.com; dkim=^google$
- Proofpoint Email Security [Proofpoint]: mx=pphosted.com, ppe-hosted.com; spf=pphosted.com, ppe-hosted.com
- Mimecast [Mimecast]: mx=mimecast.com, mimecast-offshore.com; spf=mimecast.com
- Barracuda Email Security [Barracuda]: mx=barracudanetworks.com; spf=barracudanetworks.com
- Cisco Secure Email [Cisco]: mx=iphmx.com; spf=iphmx.com
- Symantec Email Security.cloud [Broadcom]: mx=messagelabs.com; spf=messagelabs.com
- Trend Micro Email Security [Trend Micro]: mx=tmes.trendmicro; spf=tmes.trendmicro
- Forcepoint Email Security [Forcepoint]: mx=mailcontrol.com
- Hornetsecurity [Hornetsecurity]: mx=hornetsecurity.com; spf=hornetsecurity.com
- Libraesva Email Security [Libraesva]: mx=libraesva.com, esvacloud.com; spf=libraesva.com, esvacloud.com
- Retarus [Retarus]: mx=retarus.com, retarus.de; spf=retarus.com, retarus.net
- Zoho Mail [Zoho]: mx=zoho.com, zoho.eu, zoho.in; spf=zoho.com, zoho.eu; txt=^zoho-verification=
- Fastmail [Fastmail]: mx=messagingengine.com; spf=messagingengine.com
- Proton Mail [Proton]: mx=protonmail.ch; spf=protonmail.ch; txt=^protonmail-verification=
- Yandex Mail [Yandex]: mx=yandex.net, yandex.ru; spf=_spf.yandex.net
- OVHcloud Mail [OVHcloud]: mx=mail.ovh.net, mx.ovh.net; spf=mx.ovh.com
- IONOS Mail [IONOS]: mx=ionos.com, ionos.it, ionos.de, kundenserver.de, 1and1.com; spf=ionos.com, perfora.net, kundenserver.de
- Aruba Mail and PEC [Aruba]: mx=.aruba.it$; spf=.aruba.it$
- Register.it Mail [Team.blue]: mx=.register.it$; spf=.register.it$
- Libero Mail [Libero]: mx=.libero.it$; spf=.libero.it$
- GoDaddy Email [GoDaddy]: mx=secureserver.net; spf=secureserver.net
- Rackspace Email [Rackspace]: mx=emailsrvr.com; spf=emailsrvr.com
- Namecheap Private Email [Namecheap]: mx=privateemail.com; spf=privateemail.com
- Hostinger Mail [Hostinger]: mx=hostinger.com; spf=hostinger.com
- Gandi Mail [Gandi]: mx=mail.gandi.net; spf=_mailcust.gandi.net
- Cloudflare Email Routing [Cloudflare]: mx=mx.cloudflare.net; spf=_spf.mx.cloudflare.net

## sending — Email delivery and marketing
- Amazon SES [Amazon]: spf=amazonses.com; cname=dkim.amazonses.com; mx=amazonses.com
- SendGrid [Twilio]: spf=sendgrid.net; cname=.sendgrid.net$
- Mailgun [Sinch]: spf=mailgun.org; cname=.mailgun.org$; mx=mailgun.org
- Mailchimp and Mandrill [Intuit]: spf=servers.mcsv.net, mandrillapp.com; cname=.mcsv.net$, .mandrillapp.com$; dkim=^mandrill$
- Brevo (Sendinblue) [Brevo]: spf=sendinblue.com, brevo.com; cname=.sendinblue.com$, .brevo.com$; txt=^brevo-code
- Postmark [ActiveCampaign]: spf=mtasv.net; cname=.mtasv.net$
- SparkPost [Bird]: spf=sparkpostmail.com; cname=.sparkpostmail.com$
- Mailjet [Sinch]: spf=mailjet.com; cname=.mailjet.com$
- Klaviyo [Klaviyo]: spf=klaviyo.com; cname=.klaviyomail.com$, .klaviyo.com$
- Constant Contact [Constant Contact]: spf=constantcontact.com; cname=.constantcontact.com$
- Campaign Monitor [Marigold]: spf=cmail1.com, cmail2.com, cmail3.com; cname=.cmail1.com$, .cmail2.com$, .cmail3.com$
- Marketo [Adobe]: spf=mktomail.com; cname=.mktoweb.com$
- Salesforce Marketing Cloud [Salesforce]: spf=exacttarget.com; cname=.exacttarget.com$, .marketingcloudapis.com$
- Pardot [Salesforce]: spf=pardot.com; cname=.pardot.com$
- ActiveCampaign [ActiveCampaign]: spf=activehosted.com; cname=.activehosted.com$

## dmarc — DMARC and mail authentication services
- dmarcian [dmarcian]: rua=dmarcian.com, dmarcian.eu
- Valimail [Valimail]: rua=valimail.com
- Agari [Fortra]: rua=agari.com
- Proofpoint Email Fraud Defense [Proofpoint]: rua=proofpoint.com
- Red Sift OnDMARC [Red Sift]: rua=ondmarc.redsift.cloud, redsift.cloud
- EasyDMARC [EasyDMARC]: rua=easydmarc.com, easydmarc.us
- PowerDMARC [PowerDMARC]: rua=powerdmarc.com
- Postmark DMARC [ActiveCampaign]: rua=dmarc.postmarkapp.com
- Cloudflare DMARC Management [Cloudflare]: rua=dmarc-reports.cloudflare.net
- Sendmarc [Sendmarc]: rua=sendmarc.com
- URIports [URIports]: rua=uriports.com
- Mailhardener [Mailhardener]: rua=mailhardener.com

## dns — DNS hosting
- Cloudflare DNS [Cloudflare]: ns=ns.cloudflare.com
- Amazon Route 53 [Amazon]: ns=awsdns
- Azure DNS [Microsoft]: ns=azure-dns
- Google Cloud DNS [Google]: ns=googledomains.com, ns-cloud-
- Akamai Edge DNS [Akamai]: ns=.akam.net$
- NS1 [IBM]: ns=nsone.net
- Dyn [Oracle]: ns=dynect.net
- UltraDNS [Vercara]: ns=ultradns
- Verisign DNS [Verisign]: ns=verisigndns.com
- GoDaddy DNS [GoDaddy]: ns=domaincontrol.com
- Namecheap DNS [Namecheap]: ns=registrar-servers.com
- OVHcloud DNS [OVHcloud]: ns=.ovh.net$, .anycast.me$
- IONOS DNS [IONOS]: ns=ui-dns.
- Aruba DNS [Aruba]: ns=.aruba.it$
- Register.it DNS [Team.blue]: ns=.register.it$
- Gandi DNS [Gandi]: ns=.gandi.net$
- Hetzner DNS [Hetzner]: ns=.hetzner.com$, .your-server.de$
- DigitalOcean DNS [DigitalOcean]: ns=.digitalocean.com$
- Hurricane Electric DNS [Hurricane Electric]: ns=.he.net$
- Wix DNS [Wix]: ns=wixdns.net
- Squarespace DNS [Squarespace]: ns=squarespacedns.com
- Vercel DNS [Vercel]: ns=vercel-dns.com
- DNSimple [DNSimple]: ns=dnsimple.com
- ClouDNS [ClouDNS]: ns=cloudns.net
- Infomaniak DNS [Infomaniak]: ns=infomaniak.ch
- MarkMonitor DNS [MarkMonitor]: ns=.markmonitor.com$
- CSC Global DNS [CSC]: ns=cscdns.net, cscglobal.com

## edge — CDN, WAF and DDoS protection
- Cloudflare (CDN and WAF) [Cloudflare]: asn=13335; cname=.cloudflare.net$, cdn.cloudflare.com
- Akamai [Akamai]: asn=20940, 16625; cname=.akamai.net$, .akamaiedge.net$, .edgekey.net$, .edgesuite.net$, .akamaized.net$, .akamaitechnologies.com$
- Fastly [Fastly]: asn=54113; cname=.fastly.net$, .fastlylb.net$
- Amazon CloudFront [Amazon]: cname=.cloudfront.net$
- Azure Front Door and CDN [Microsoft]: cname=.azurefd.net$, .azureedge.net$
- Imperva [Thales]: asn=19551; cname=.incapdns.net$, .impervadns.net$
- Sucuri [GoDaddy]: asn=30148; cname=.sucuri.net$
- Edgio [Edgio]: asn=15133, 22822; cname=.edgecastcdn.net$, .llnwd.net$, .edgio.net$
- StackPath [StackPath]: cname=.stackpathdns.com$, .stackpathcdn.com$
- CDN77 [DataCamp]: asn=60068; cname=.cdn77.org$, .cdn77.com$
- Bunny CDN [Bunny]: cname=.b-cdn.net$

## hosting — Hosting and cloud platforms
- Amazon Web Services [Amazon]: asn=16509, 14618; cname=.amazonaws.com$, .elasticbeanstalk.com$, .awsglobalaccelerator.com$
- Microsoft Azure [Microsoft]: asn=8075; cname=.azurewebsites.net$, .cloudapp.azure.com$, .cloudapp.net$, .trafficmanager.net$, .azure-api.net$, .blob.core.windows.net$
- Google Cloud [Google]: asn=15169, 396982; cname=.appspot.com$, .run.app$, .cloudfunctions.net$, .web.app$, .firebaseapp.com$, ghs.googlehosted.com
- Oracle Cloud [Oracle]: asn=31898; cname=.oraclecloud.com$
- IBM Cloud [IBM]: asn=36351
- Alibaba Cloud [Alibaba]: asn=45102, 37963; cname=.aliyuncs.com$
- Tencent Cloud [Tencent]: asn=132203, 45090
- OVHcloud [OVHcloud]: asn=16276; cname=.ovhcloud.com$
- Hetzner [Hetzner]: asn=24940
- DigitalOcean [DigitalOcean]: asn=14061; cname=.digitaloceanspaces.com$, .ondigitalocean.app$
- Akamai Connected Cloud (Linode) [Akamai]: asn=63949
- Vultr [Vultr]: asn=20473
- Scaleway [Scaleway]: asn=12876
- IONOS [IONOS]: asn=8560
- Aruba Cloud and Hosting [Aruba]: asn=31034
- Seeweb [Seeweb]: asn=12637
- Netlify [Netlify]: cname=.netlify.app$, .netlify.com$
- Vercel [Vercel]: cname=.vercel.app$, .vercel-dns.com$
- Heroku [Salesforce]: cname=.herokuapp.com$, .herokudns.com$
- GitHub Pages [Microsoft]: cname=.github.io$; txt=^_github-pages-challenge
- Cloudflare Pages and Workers [Cloudflare]: cname=.pages.dev$, .workers.dev$
- WP Engine [WP Engine]: cname=.wpengine.com$, .wpenginepowered.com$
- WordPress.com [Automattic]: cname=.wordpress.com$
- Wix [Wix]: cname=.wixdns.net$, .wix.com$
- Squarespace [Squarespace]: cname=.squarespace.com$
- Webflow [Webflow]: cname=.webflow.io$
- Kinsta [Kinsta]: cname=.kinsta.cloud$
- Pantheon [Pantheon]: cname=.pantheonsite.io$
- Acquia [Acquia]: cname=.acquia-sites.com$
- Adobe Experience Manager Cloud [Adobe]: cname=.adobeaemcloud.com$

## network — Network operators and transit
- TIM [TIM]: asn=3269
- TIM Sparkle [TIM]: asn=6762
- Vodafone Italia [Vodafone]: asn=30722
- Fastweb [Swisscom]: asn=12874
- WindTre [WindTre]: asn=1267
- Iliad Italia [Iliad]: asn=29447
- Orange [Orange]: asn=3215
- Deutsche Telekom [Deutsche Telekom]: asn=3320
- Telefónica [Telefónica]: asn=3352
- Telia [Telia]: asn=1299
- Lumen [Lumen]: asn=3356
- Cogent [Cogent]: asn=174

## identity — Identity and access
- Microsoft Entra ID [Microsoft]: cname=enterpriseregistration.windows.net, enterpriseenrollment.manage.microsoft.com, .b2clogin.com$
- Okta [Okta]: cname=.okta.com$, .oktapreview.com$, .okta-emea.com$; txt=^okta-domain-verification
- Auth0 [Okta]: cname=.auth0.com$; txt=^auth0
- Ping Identity [Ping Identity]: cname=.pingone.com$, .pingidentity.com$
- OneLogin [One Identity]: cname=.onelogin.com$
- Duo Security [Cisco]: cname=.duosecurity.com$
- CyberArk [CyberArk]: cname=.cyberark.cloud$, .idaptive.app$

## security — Security services
- Zscaler [Zscaler]: cname=.zscaler.net$, .zscloud.net$, .zscalerthree.net$
- Netskope [Netskope]: cname=.goskope.com$
- Cisco Umbrella [Cisco]: cname=.umbrella.com$, .opendns.com$
- Forcepoint [Forcepoint]: cname=.forcepoint.net$

## collab — Collaboration and productivity
- Microsoft Teams [Microsoft]: cname=webdir.online.lync.com, sipdir.online.lync.com
- Atlassian [Atlassian]: cname=.atlassian.net$, .jira.com$; txt=^atlassian-domain-verification=
- Slack [Salesforce]: txt=^slack-domain-verification
- Zoom [Zoom]: cname=.zoom.us$; txt=^zoom_verify
- Webex [Cisco]: cname=.webex.com$, .ciscospark.com$
- Box [Box]: cname=.box.com$; txt=^box-domain-verification=
- Dropbox [Dropbox]: txt=^dropbox-domain-verification=
- Notion [Notion]: txt=^notion-domain-verification=
- Asana [Asana]: txt=^asana-verification
- Monday.com [Monday.com]: txt=^monday-verification
- DocuSign [DocuSign]: cname=.docusign.net$; txt=^docusign=
- Adobe [Adobe]: txt=^adobe-idp-site-verification=, ^adobe-sign-verification=
- Canva [Canva]: txt=^canva-site-verification=
- Apple Business [Apple]: txt=^apple-domain-verification=

## crm — CRM, support and customer service
- Salesforce [Salesforce]: cname=.force.com$, .salesforce.com$, .salesforce-sites.com$
- HubSpot [HubSpot]: spf=hubspotemail.net; cname=.hubspot.net$, .hubspotemail.net$, .hs-sites.com$
- Zendesk [Zendesk]: cname=.zendesk.com$; txt=^zendeskverification
- Freshworks [Freshworks]: cname=.freshdesk.com$, .freshservice.com$, .myfreshworks.com$
- Intercom [Intercom]: cname=.intercom.io$, .intercom.help$
- Help Scout [Help Scout]: cname=.helpscoutdocs.com$, .helpscout.net$
- Atlassian Statuspage [Atlassian]: cname=.statuspage.io$
- ServiceNow [ServiceNow]: cname=.service-now.com$
- Microsoft Dynamics 365 [Microsoft]: cname=.dynamics.com$
- SAP Cloud [SAP]: cname=.ondemand.com$
- Oracle NetSuite [Oracle]: cname=.netsuite.com$
- Typeform [Typeform]: cname=.typeform.com$

## commerce — E-commerce and payments
- Shopify [Shopify]: cname=.myshopify.com$
- Stripe [Stripe]: txt=^stripe-verification=
- Adyen [Adyen]: cname=.adyen.com$
- Salesforce Commerce Cloud [Salesforce]: cname=.demandware.net$
- BigCommerce [BigCommerce]: cname=.bigcommerce.com$
- Adobe Commerce Cloud [Adobe]: cname=.magentosite.cloud$

## hr — HR and recruiting
- Workday [Workday]: cname=.myworkdayjobs.com$, .workday.com$
- SAP SuccessFactors [SAP]: cname=.successfactors.com$, .successfactors.eu$
- Greenhouse [Greenhouse]: cname=.greenhouse.io$
- Lever [Employ]: cname=.lever.co$
- SmartRecruiters [SmartRecruiters]: cname=.smartrecruiters.com$
- Teamtailor [Teamtailor]: cname=.teamtailor.com$
- Personio [Personio]: cname=.personio.de$, .personio.com$
- Recruitee [Recruitee]: cname=.recruitee.com$
- BambooHR [BambooHR]: cname=.bamboohr.com$

## analytics — Analytics, advertising and consent
- Meta (domain verification) [Meta]: txt=^facebook-domain-verification=
- Pinterest [Pinterest]: txt=^pinterest-site-verification=
- TikTok [ByteDance]: txt=^tiktok-domain-verification
- Cookiebot [Usercentrics]: cname=.cookiebot.com$
- OneTrust [OneTrust]: cname=.onetrust.com$, .cookielaw.org$
- Adobe Analytics [Adobe]: cname=.omtrdc.net$, .2o7.net$
- Matomo Cloud [Matomo]: cname=.matomo.cloud$
- Optimizely [Optimizely]: cname=.optimizely.com$
