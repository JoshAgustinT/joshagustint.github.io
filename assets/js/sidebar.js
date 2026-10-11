// Shared sidebar for every page.
// Edit the menu here; each page includes:
//   <div id="sidebar"></div>
//   <script src="assets/js/sidebar.js"></script>
// This must load before main.js, which wires up the toggle and submenu openers.

document.getElementById('sidebar').innerHTML = `
	<div class="inner">
		<!-- Menu -->
		<nav id="menu">
			<header class="major">
				<h2>Joshua Tlatelpa-Agustin</h2>
			</header>

			<ul>
				<li><a href="index.html">Homepage</a></li>
				<!-- <li><a href="projects.html">Projects</a></li> -->
				<li><a href="research.html">Research</a></li>
				<!-- <li><a href="coursework.html">Academics</a></li> -->
				<li>
					<span class="opener">Hobbies</span>
					<ul>
						<li><a href="photography.html">Photography</a></li>
						<li><a href="projects.html">Projects</a></li>
						<!-- <li><a href="music.html">Music</a></li> -->
						<!-- <li><a href="hardware.html">Tech Stuff</a></li> -->
					</ul>
				</li>
				<li><a href="about.html">About</a></li>
			</ul>
		</nav>
	</div>
`;
