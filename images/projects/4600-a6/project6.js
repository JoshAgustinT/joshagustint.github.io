/* * 
 * CS4600      - Introduction to Computer Graphics
 * Project 6   - Ray Tracing
 * Instructor  - Yin Yang
 * Student     - Joshua Tlatelpa-Agustin [u1399218]
 **/

var raytraceFS = `
struct Ray {
	vec3 pos;
	vec3 dir;
};

struct Material {
	vec3  k_d;	// diffuse coefficient
	vec3  k_s;	// specular coefficient
	float n;	// specular exponent
};

struct Sphere {
	vec3     center;
	float    radius;
	Material mtl;
};

struct Light {
	vec3 position;
	vec3 intensity;
};

struct HitInfo {
	float    t;
	vec3     position;
	vec3     normal;
	Material mtl;
};

float bias = 0.0001;

uniform Sphere spheres[ NUM_SPHERES ];
uniform Light  lights [ NUM_LIGHTS  ];
uniform samplerCube envMap;
uniform int bounceLimit;

bool IntersectRay( inout HitInfo hit, Ray ray );

// Shades the given point and returns the computed color.
vec3 Shade( Material mtl, vec3 position, vec3 normal, vec3 view )
{	
	vec3 color = vec3(0,0,0);
	for ( int i=0; i<NUM_LIGHTS; ++i ) {

	//TO-DO: Check for shadows
	Ray shadowRay;
	shadowRay.pos = position ;
	shadowRay.dir = normalize (lights[i].position - position );
	HitInfo shadowHit;

	bool interesect = IntersectRay(shadowHit, shadowRay);
	if (interesect) {
		continue;
	}

	//TO-DO: If not shadowed, perform shading using the Blinn model
	vec3 lightDir = normalize(shadowRay.dir);
	vec3 halfVector = normalize(view + lightDir);
	float diffuse = max(0.0, dot(normal, lightDir));
	float specular = pow(max(0.0, dot(normal, halfVector)), mtl.n);
	color += lights[i].intensity * ( (mtl.k_d * diffuse) + (mtl.k_s * specular) );

	} //end for-loop
return color;


	
}//end Shade()

// Intersects the given ray with all spheres in the scene
// and updates the given HitInfo using the information of the sphere
// that first intersects with the ray.
// Returns true if an intersection is found.
bool IntersectRay( inout HitInfo hit, Ray ray )
{

	hit.t = 1e30;
	bool foundHit = false;
	for ( int i=0; i<NUM_SPHERES; ++i ) {
		// TO-DO: Test for ray-sphere intersection
		vec3 oc = ray.pos - spheres[i].center;
		float a = dot(ray.dir, ray.dir);
		float b = 2.0 * dot(oc, ray.dir);
		float c = dot(oc, oc) - spheres[i].radius * spheres[i].radius;
		float discriminant = b*b - 4.0*a*c;

		// TO-DO: If intersection is found, update the given HitInfo
		if (discriminant >= 0.0) {
			float t1 = (-b - sqrt(discriminant)) / (2.0 * a);
			float t2 = (-b + sqrt(discriminant)) / (2.0 * a);
			float t = min(t1, t2); 

			if (t > bias && t <= hit.t) {
				hit.t = t;
				hit.position = ray.pos + (t*ray.dir); //solving x = p+td
				hit.normal = normalize(hit.position - spheres[i].center);
				hit.mtl = spheres[i].mtl;

				foundHit = true;
			}//end if (discriminant > 0.0)

		}//end for-loop
	}
	
	return foundHit;
}



// Given a ray, returns the shaded color where the ray intersects a sphere.
// If the ray does not hit a sphere, returns the environment color.
vec4 RayTracer( Ray ray )
{

	//Ray {vec3 pos, vec3 dir}
	//HitInfo {float t, vec3 position,vec3 normal,Material mtl}

	HitInfo hit;
	if ( IntersectRay( hit, ray ) ) {
		vec3 view = normalize( -ray.dir );
		vec3 clr = Shade( hit.mtl, hit.position, hit.normal, view );
		
		// Compute reflections
		vec3 k_s = hit.mtl.k_s;
		for ( int bounce=0; bounce<MAX_BOUNCES; ++bounce ) {
			if ( bounce >= bounceLimit ) break;
			if ( hit.mtl.k_s.r + hit.mtl.k_s.g + hit.mtl.k_s.b <= 0.0 ) break;
			
			Ray r;	// this is the reflection ray
			HitInfo h;	// reflection hit info
			
			// TO-DO: Initialize the reflection ray
			r.dir = normalize( reflect(ray.dir, hit.normal) ) ;
			r.pos = hit.position; 
			
			if ( IntersectRay( h, r ) ) {
				// TO-DO: Hit found, so shade the hit point
				clr += k_s* Shade(h.mtl, h.position, h.normal, normalize(-r.dir) );	
				// TO-DO: Update the loop variables for tracing the next reflection ray
				hit = h;
				ray = r;
				k_s = k_s* h.mtl.k_s;
				
			}
			 else {
				// The refleciton ray did not intersect with anything,
				// so we are using the environment color
				clr += k_s * textureCube( envMap, r.dir.xzy ).rgb;
				break;	// no more reflections
			}
		}
		return vec4( clr, 1 );	// return the accumulated color, including the reflections
	
	}//end if( IntersectRay( hit, ray ) )
	
	else {
		return vec4( textureCube( envMap, ray.dir.xzy ).rgb, 1 );	// return the environment color
	}

}//end RayTracer()

`;


