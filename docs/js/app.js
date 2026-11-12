// PCForge (version estatica) - APLICACION DELIBERADAMENTE VULNERABLE (practicas)
// Usuarios ficticios. La "autenticacion" ocurre en el navegador.
var USUARIOS = [
  { usuario: "ana",   clave: "ana123",     rol: "cliente" },
  { usuario: "luis",  clave: "luis123",    rol: "cliente" },
  { usuario: "admin", clave: "Admin#2026", rol: "admin" }
];

function sesion() {
  try { return JSON.parse(localStorage.getItem("sesion")); } catch (e) { return null; }
}
function param(n) { return new URLSearchParams(location.search).get(n); }
function eur(n) { return Number(n).toFixed(2) + " €"; }

function cabecera() {
  var s = sesion();
  var cuenta = s
    ? '<span>Hola, ' + s.usuario + '</span><a href="pedidos.html">Mis pedidos</a>' +
      (s.rol === "admin" ? '<a href="admin.html">Administracion</a>' : '') +
      '<a href="#" id="salir">Salir</a>'
    : '<a href="login.html">Entrar</a>';
  document.getElementById("cab").innerHTML =
    '<div class="aviso">Entorno de practicas con vulnerabilidades intencionadas. Datos ficticios. Version 1.0.0-estatica.</div>' +
    '<header class="top"><a class="logo" href="index.html">PC<b>Forge</b></a>' +
    '<form action="index.html" method="get" role="search"><input type="search" name="q" placeholder="Buscar componentes" aria-label="Buscar componentes"><button type="submit">Buscar</button></form>' +
    '<nav class="cuenta">' + cuenta + '</nav></header>';
  var salir = document.getElementById("salir");
  if (salir) salir.onclick = function (e) { e.preventDefault(); localStorage.removeItem("sesion"); location.href = "index.html"; };
}

function tarjeta(p) {
  return '<article class="card"><small>' + p.categoria + '</small>' +
    '<h3><a href="producto.html?id=' + p.id + '">' + p.nombre + '</a></h3>' +
    '<span>' + p.descripcion + '</span><span class="precio">' + eur(p.precio) + '</span></article>';
}
document.addEventListener("DOMContentLoaded", cabecera);
