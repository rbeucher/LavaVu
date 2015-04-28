#version 120 //Required to use gl_PointCoord
varying float vSmooth;
varying vec3 vPosEye;
varying float vPointType;
varying float vPointSize;
uniform int uPointType;
uniform float uOpacity;
uniform bool uTextured;
uniform sampler2D uTexture;

void main(void)
{
   float alpha = gl_Color.a;
   if (uOpacity > 0.0) alpha *= uOpacity;
   gl_FragColor = gl_Color;
   float pointType = uPointType;
   if (vPointType >= 0) pointType = vPointType;
   pointType = floor(pointType + 0.5);

   //Textured?
   if (uTextured)
      gl_FragColor = texture2D(uTexture, gl_PointCoord);

   //Flat, square points, fastest
   if (pointType == 4 || vSmooth < 0.0) 
      return;

   //Calculate normal from point/tex coordinates
   vec3 N;
   N.xy = gl_PointCoord * 2.0 - vec2(1.0);    
   float R = dot(N.xy, N.xy);
   //Discard if outside circle
   if (R > 1.0) discard;
   //Anti-aliased edges for sphere types
   if (pointType > 1)
   {
     float edge = vPointSize - R * vPointSize;
     if (edge <= 4.0) 
        alpha *= (0.25 * edge);
   }
   //Discard if transparent
   if (alpha < 0.01) discard;

   if (pointType < 2)
   {
      if (pointType == 0)
         gl_FragColor.a = alpha * 1.0-sqrt(R);  //Gaussian
      else
         gl_FragColor.a = alpha * 1.0-R;      //Linear
      return;
   }

   N.z = sqrt(1.0-R);

   //Calculate diffuse lighting
   vec3 lightDir = normalize(vec3(0,0,0) - vPosEye);
   float diffuse = max(0.0, dot(lightDir, N));

   //Compute the specular term
   vec3 specular = vec3(0.0,0.0,0.0);
   if (pointType == 3 && diffuse > 0.0)
   {
      float shininess = 200; //Size of highlight
      vec3 specolour = vec3(1.0, 1.0, 1.0);   //Color of light
      //Normalize the half-vector
      //vec3 halfVector = normalize(vPosEye + lightDir);
      vec3 halfVector = normalize(vec3(0.0, 0.0, 1.0) + lightDir);
      //Compute cosine (dot product) with the normal
      float NdotHV = max(dot(N, halfVector), 0.0);
      specular = specolour * pow(NdotHV, shininess);
      //specular = vec3(1.0, 0.0, 0.0);
   }

   gl_FragColor = vec4(gl_FragColor.rgb * diffuse + specular, alpha);
}
