// Public assets bypass this script; only feedback and its Access-protected admin run it.
import {feedbackRoutes} from './feedback.js';
export default {
  async fetch(request,env,ctx) {
    const feedback=await feedbackRoutes(request,env,ctx);if(feedback)return feedback;
    if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405,headers:{Allow:'GET, HEAD'}});
    return env.ASSETS.fetch(request);
  }
};
